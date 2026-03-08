"""
Collector views for E-RECYCLO
OTP-based pickup + delivery verification flow with 5km radius and vehicle matching.
"""
import io
from django.core.paginator import Paginator
from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt

from apps.client.models import PhotoPost
from .models import CollectorPickup, CollectorEarnings, CollectorPickupPayment
from .forms import AcceptPickupForm, CompletePickupForm


# Vehicle capacity mapping
VEHICLE_CAPACITY = {
    'bike': ['small', 'medium'],
    'scooter': ['small', 'medium'],
    'auto': ['small', 'medium', 'large'],
    'van': ['small', 'medium', 'large', 'very_large'],
    'tempo': ['small', 'medium', 'large', 'very_large'],
    'pickup': ['small', 'medium', 'large', 'very_large'],
}


def calculate_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return round(6371 * 2 * asin(sqrt(a)), 2)


def can_handle_item(collector, item):
    """Check if collector's vehicle can handle the item based on size"""
    try:
        cp = collector.collector_profile
        vehicle_type = cp.vehicle_type or 'bike'
        item_size = item.item_size or 'medium'  # Default to medium
        return item_size in VEHICLE_CAPACITY.get(vehicle_type, ['small', 'medium'])
    except:
        return True  # If no profile, assume can handle


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    profile_completion = request.user.profile_completion
    if profile_completion.approval_status != 'approved':
        messages.warning(request, 'Your profile is pending approval.')
    
    earnings, _ = CollectorEarnings.objects.get_or_create(collector=request.user)
    
    # Get collector's location and vehicle type
    try:
        cp = request.user.collector_profile
        collector_lat, collector_lon = cp.latitude, cp.longitude
        vehicle_type = cp.vehicle_type or 'bike'
    except:
        collector_lat, collector_lon = None, None
        vehicle_type = 'bike'
    
    # Count available pickups within 5km that this collector can handle
    available_count = 0
    if collector_lat and collector_lon:
        # Regular pickups (client → vendor)
        pending_pickups = PhotoPost.objects.filter(status='pickup_scheduled', collector__isnull=True)
        for item in pending_pickups:
            dist = calculate_distance(item.latitude, item.longitude, collector_lat, collector_lon)
            if dist <= 5 and can_handle_item(request.user, item):
                available_count += 1
        
        # Return pickups (vendor → client)
        return_pickups = PhotoPost.objects.filter(status='return_requested', return_collector__isnull=True)
        for item in return_pickups:
            try:
                vendor_lat = item.vendor.vendor_profile.latitude
                vendor_lon = item.vendor.vendor_profile.longitude
                dist = calculate_distance(vendor_lat, vendor_lon, collector_lat, collector_lon)
                if dist <= 5 and can_handle_item(request.user, item):
                    available_count += 1
            except:
                continue
    
    active_pickups = CollectorPickup.objects.filter(
        collector=request.user, 
        status__in=['assigned', 'accepted', 'in_progress']
    ).count()
    
    recent_pickups = CollectorPickup.objects.filter(
        collector=request.user
    ).select_related('photo_post').order_by('-created_at')[:5]
    
    return render(request, 'collector/dashboard.html', {
        'available_pickups': available_count,
        'my_active_pickups': active_pickups,
        'earnings': earnings,
        'recent_pickups': recent_pickups,
        'profile_completion': profile_completion,
        'vehicle_type': vehicle_type,
    })


@login_required
def update_location(request):
    """
    AJAX POST — update collector's live base location.
    Called when collector taps 'Update My Location' on the available_pickups page.
    Writes new lat/lng to CollectorProfile and returns JSON.
    """
    if not request.user.is_collector:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required.'}, status=405)

    try:
        lat = float(request.POST.get('latitude', ''))
        lng = float(request.POST.get('longitude', ''))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid coordinates.'}, status=400)

    # Basic sanity check — India bounding box
    if not (6.0 <= lat <= 37.0 and 68.0 <= lng <= 98.0):
        return JsonResponse({'success': False, 'error': 'Coordinates outside expected range.'}, status=400)

    try:
        cp = request.user.collector_profile
        cp.latitude  = lat
        cp.longitude = lng
        cp.save(update_fields=['latitude', 'longitude'])
        return JsonResponse({
            'success': True,
            'latitude':  round(lat, 6),
            'longitude': round(lng, 6),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



# ── AVAILABLE PICKUPS ─────────────────────────────────────────────────────────
@login_required
def available_pickups(request):
    """Show all available pickups within 5km that the collector can handle.
    Includes: regular pickups (client→vendor) AND return pickups (vendor→client)
    """
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
        
    pc = request.user.profile_completion
    if pc.approval_status != 'approved':
        messages.error(request, 'Your profile must be approved to view available pickups.')
        from django.urls import reverse
        return redirect(f"{reverse('accounts:complete_collector_profile')}?unapproved_redirect=true")
    
    # Get collector's location and vehicle type
    try:
        cp = request.user.collector_profile
        collector_lat, collector_lon = cp.latitude, cp.longitude
        vehicle_type = cp.vehicle_type or 'bike'
    except:
        messages.error(request, 'Please complete your profile with location.')
        return redirect('accounts:complete_collector_profile')
    
    if not collector_lat or not collector_lon:
        messages.error(request, 'Please add your location to see nearby pickups.')
        return redirect('accounts:complete_collector_profile')
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REGULAR PICKUPS: Client → Vendor (status='pickup_scheduled', no collector)
    # This also includes VENDOR TRANSFERS (pickup from previous vendor)
    # ═══════════════════════════════════════════════════════════════════════════
    regular_pending = PhotoPost.objects.filter(
        status='pickup_scheduled',
        collector__isnull=True
    ).select_related('user', 'vendor').order_by('-created_at')
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RETURN PICKUPS: Vendor → Client (status='return_requested', no return_collector)
    # ═══════════════════════════════════════════════════════════════════════════
    return_pending = PhotoPost.objects.filter(
        status='return_requested',
        return_collector__isnull=True
    ).select_related('user', 'vendor').order_by('-created_at')
    
    nearby_pickups = []
    
    # Process regular pickups (could be client→vendor OR vendor→vendor transfer)
    for item in regular_pending:
        # Check if this is a vendor-to-vendor transfer
        is_vendor_transfer = item.vendor_remarks and item.vendor_remarks.startswith('TRANSFER_FROM_VENDOR:')
        previous_vendor = None
        from_location = item.address
        dist = 0.0

        if is_vendor_transfer:
            # Extract previous vendor ID and get their location
            try:
                prev_vendor_id = int(item.vendor_remarks.split(':')[1])
                from apps.accounts.models import Account
                previous_vendor = Account.objects.get(pk=prev_vendor_id)
                # For vendor transfer, calculate distance from PREVIOUS vendor
                prev_vp = previous_vendor.vendor_profile
                dist = calculate_distance(prev_vp.latitude, prev_vp.longitude, collector_lat, collector_lon)
                from_location = f"{previous_vendor.get_full_name()}'s facility"
                from_lat, from_lon = prev_vp.latitude, prev_vp.longitude
            except:
                # Fallback to client location
                dist = calculate_distance(item.latitude, item.longitude, collector_lat, collector_lon)
                from_location = item.address
                from_lat, from_lon = item.latitude, item.longitude
                is_vendor_transfer = False
        else:
            # Regular pickup from client
            dist = calculate_distance(item.latitude, item.longitude, collector_lat, collector_lon)
            from_location = item.address
            from_lat, from_lon = item.latitude, item.longitude
        
        # Only process if within 5km radius
        if dist <= 5:
            # Destination coordinates (Vendor)
            to_lat, to_lon = None, None
            if item.vendor:
                to_lat, to_lon = item.vendor.vendor_profile.latitude, item.vendor.vendor_profile.longitude

            # Capacity check
            item_size = item.item_size or 'medium'
            can_handle = item_size in VEHICLE_CAPACITY.get(vehicle_type, ['small', 'medium'])
            
            # Distance for earnings (Source to Destination)
            if is_vendor_transfer:
                try:
                    distance_km = calculate_distance(from_lat, from_lon, to_lat, to_lon)
                except:
                    distance_km = 5.0
            else:
                try:
                    distance_km = calculate_distance(from_lat, from_lon, to_lat, to_lon)
                except:
                    distance_km = 5.0

            # Standardized Earnings Calculation
            base_fee = Decimal('39.00')
            per_km_rate = Decimal('8.00')
            distance_fee = (Decimal(str(distance_km)) * per_km_rate).quantize(Decimal('0.01'))
            
            handling_fee = {
                'smartphone': Decimal('20.00'),
                'laptop': Decimal('30.00'),
                'monitor': Decimal('50.00'),
                'appliance': Decimal('60.00'),
                'battery': Decimal('15.00'),
                'other': Decimal('25.00'),
            }.get(item.ai_category, Decimal('25.00'))
            
            total_payout = base_fee + distance_fee + handling_fee

            nearby_pickups.append({
                'item': item,
                'distance': round(dist, 2),
                'can_handle': can_handle,
                'pickup_type': 'vendor_transfer' if is_vendor_transfer else 'regular',
                'from_location': from_location,
                'from_lat': from_lat,
                'from_lon': from_lon,
                'to_location': f"{item.vendor.get_full_name()}'s facility" if item.vendor else 'Vendor',
                'to_lat': to_lat,
                'to_lon': to_lon,
                'previous_vendor': previous_vendor,
                'total_payout': round(total_payout, 2),
                'reason': None if can_handle else f"Requires larger vehicle (item is {item.get_item_size_display() if item.item_size else 'medium-sized'})"
            })
    
    # Process return pickups (vendor → client)
    for item in return_pending:
        # For returns, calculate distance from VENDOR's location to collector
        try:
            vendor_lat = item.vendor.vendor_profile.latitude
            vendor_lon = item.vendor.vendor_profile.longitude
            dist = calculate_distance(vendor_lat, vendor_lon, collector_lat, collector_lon)
        except:
            dist = 999  # Skip if no vendor location
            continue
        
        if dist <= 5:
            item_size = item.item_size or 'medium'
            can_handle = item_size in VEHICLE_CAPACITY.get(vehicle_type, ['small', 'medium'])
            
            # Calculate distance for earnings (Vendor → Client)
            try:
                distance_km = calculate_distance(vendor_lat, vendor_lon, item.latitude, item.longitude)
            except:
                distance_km = 5.0

            # Standardized Earnings Calculation (Matches accept_pickup logic)
            base_fee = Decimal('39.00')
            per_km_rate = Decimal('8.00')
            distance_fee = (Decimal(str(distance_km)) * per_km_rate).quantize(Decimal('0.01'))
            
            handling_fee = {
                'smartphone': Decimal('20.00'),
                'laptop': Decimal('30.00'),
                'monitor': Decimal('50.00'),
                'appliance': Decimal('60.00'),
                'battery': Decimal('15.00'),
                'other': Decimal('25.00'),
            }.get(item.ai_category, Decimal('25.00'))
            
            total_payout = base_fee + distance_fee + handling_fee

            nearby_pickups.append({
                'item': item,
                'distance': round(dist, 2),
                'can_handle': can_handle,
                'pickup_type': 'return',  # Vendor → Client
                'from_location': f"{item.vendor.get_full_name()}'s facility" if item.vendor else 'Vendor',
                'from_lat': vendor_lat,
                'from_lon': vendor_lon,
                'to_location': item.address,
                'to_lat': item.latitude,
                'to_lon': item.longitude,
                'total_payout': round(total_payout, 2),
                'reason': None if can_handle else f"Requires larger vehicle (item is {item.get_item_size_display() if item.item_size else 'medium-sized'})"
            })
    
    # Sort by distance
    nearby_pickups.sort(key=lambda x: x['distance'])
    
    from django.core.paginator import Paginator
    paginator = Paginator(nearby_pickups, 10)
    page_number = request.GET.get('page')
    pickups_page = paginator.get_page(page_number)
    
    return render(request, 'collector/available_pickups.html', {
        'pickups': pickups_page,
        'total_count': len(nearby_pickups),
        'vehicle_type': vehicle_type,
    })


# ── ACCEPT PICKUP ─────────────────────────────────────────────────────────────
@login_required
def accept_pickup(request, pk):
    """Collector accepts a pickup - handles both regular (client→vendor) and return (vendor→client)"""
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Try to get the item - handle race condition gracefully
    try:
        item = PhotoPost.objects.get(pk=pk)
    except PhotoPost.DoesNotExist:
        messages.warning(request, '😕 This pickup no longer exists.')
        return redirect('collector:available_pickups')
    
    # Determine if this is a regular pickup or return pickup
    is_return_pickup = item.status == 'return_requested'
    
    # Check if already taken by another collector
    if is_return_pickup:
        if item.status != 'return_requested' or item.return_collector is not None:
            messages.warning(request, f'⚡ Oops! This return pickup was just claimed by another collector.')
            return redirect('collector:available_pickups')
    else:
        if item.status != 'pickup_scheduled' or item.collector is not None:
            messages.warning(request, f'⚡ Oops! This pickup was just claimed by another collector.')
            return redirect('collector:available_pickups')
    
    # Get collector profile
    try:
        cp = request.user.collector_profile
        collector_lat, collector_lon = cp.latitude, cp.longitude
        vehicle_type = cp.vehicle_type or 'bike'
    except:
        messages.error(request, 'Please complete your profile.')
        return redirect('collector:available_pickups')
    
    # For return pickup, calculate from vendor location; for regular, from client location
    if is_return_pickup:
        try:
            vendor_lat = item.vendor.vendor_profile.latitude
            vendor_lon = item.vendor.vendor_profile.longitude
            dist = calculate_distance(vendor_lat, vendor_lon, collector_lat, collector_lon)
        except:
            messages.error(request, 'Cannot determine vendor location.')
            return redirect('collector:available_pickups')
    else:
        dist = calculate_distance(item.latitude, item.longitude, collector_lat, collector_lon)
    
    if dist > 5:
        messages.error(request, 'This pickup is outside your service area (5km radius).')
        return redirect('collector:available_pickups')
    
    # Check vehicle capacity
    item_size = item.item_size or 'medium'
    if item_size not in VEHICLE_CAPACITY.get(vehicle_type, ['small', 'medium']):
        messages.error(request, f'Your vehicle ({vehicle_type}) cannot handle this item size ({item.get_item_size_display()}).')
        return redirect('collector:available_pickups')

    # Calculate distance for earnings
    if is_return_pickup:
        # Return: vendor → client
        try:
            vendor_lat = item.vendor.vendor_profile.latitude
            vendor_lon = item.vendor.vendor_profile.longitude
            distance_km = calculate_distance(vendor_lat, vendor_lon, item.latitude, item.longitude)
        except:
            distance_km = 5.0
    else:
        # Regular: client → vendor
        try:
            vl = item.vendor.vendor_profile.latitude
            vlg = item.vendor.vendor_profile.longitude
            distance_km = calculate_distance(item.latitude, item.longitude, vl, vlg) if all([item.latitude, item.longitude, vl, vlg]) else 5.0
        except Exception:
            distance_km = 5.0

    # Calculate earnings - BASE FEE IS NOW ₹39
    base_fee = Decimal('39.00')
    per_km_rate = Decimal('8.00')
    distance_fee = (Decimal(str(distance_km)) * per_km_rate).quantize(Decimal('0.01'))
    
    handling_fee = {
        'smartphone': Decimal('20.00'),
        'laptop': Decimal('30.00'),
        'tv': Decimal('50.00'),
        'refrigerator': Decimal('60.00'),
        'washing_machine': Decimal('50.00'),
        'ac': Decimal('60.00'),
        'battery': Decimal('15.00'),
        'appliance': Decimal('25.00'),
        'cable': Decimal('10.00'),
    }.get(item.ai_category, Decimal('25.00'))
    
    total_earnings = base_fee + distance_fee + handling_fee

    if request.method == 'POST':
        # Double-check item is still available (race condition protection)
        item.refresh_from_db()
        
        if is_return_pickup:
            if item.return_collector is not None or item.status != 'return_requested':
                messages.warning(request, '⚡ Oops! This return pickup was just claimed by another collector.')
                return redirect('collector:available_pickups')
            
            # Assign return collector and update status
            item.return_collector = request.user
            item.status = 'return_pickup_scheduled'
            item.save()
            
            pickup_record = CollectorPickup.objects.create(
                collector=request.user,
                photo_post=item,
                status='accepted',
                base_fee=base_fee,
                distance_fee=distance_fee,
                total_payment=total_earnings,
            )
            
            messages.success(request, f'✅ Return pickup accepted! Pick up from vendor, deliver to client. You will earn ₹{total_earnings}')
        else:
            if item.collector is not None or item.status != 'pickup_scheduled':
                messages.warning(request, '⚡ Oops! This pickup was just claimed by another collector.')
                return redirect('collector:available_pickups')
            
            # Assign collector - triggers OTP generation in model.save()
            item.collector = request.user
            item.save()

            CollectorPickup.objects.create(
                collector=request.user,
                photo_post=item,
                status='accepted',
                base_fee=base_fee,
                distance_fee=distance_fee,
                total_payment=total_earnings,
            )
            
            # Use update_or_create to handle existing payment records (from previous transfers)
            CollectorPickupPayment.objects.update_or_create(
                pickup=item,
                defaults={
                    'collector': request.user,
                    'base_fee': base_fee,
                    'distance_fee': distance_fee,
                    'handling_fee': handling_fee,
                    'total_amount': total_earnings,
                    'distance_km': distance_km,
                    'paid': False,  # Reset payment status
                }
            )
            
            messages.success(request, f'✅ Pickup accepted! Ask the client for their Pickup OTP. You will earn ₹{total_earnings}')
        
        e, _ = CollectorEarnings.objects.get_or_create(collector=request.user)
        e.total_pickups += 1
        e.save()

        return redirect('collector:my_pickups')

    return render(request, 'collector/accept_pickup.html', {
        'item': item,
        'is_return_pickup': is_return_pickup,
        'distance_km': distance_km,
        'estimated_time': round(distance_km * 2.5),
        'base_fee': base_fee,
        'per_km_rate': per_km_rate,
        'distance_fee': distance_fee,
        'handling_fee': handling_fee,
        'total_earnings': total_earnings,
    })


# ── MY PICKUPS ────────────────────────────────────────────────────────────────
@login_required
def my_pickups(request):
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
        
    pc = request.user.profile_completion
    if pc.approval_status != 'approved':
        messages.error(request, 'Your profile must be approved to manage your pickups.')
        from django.urls import reverse
        return redirect(f"{reverse('accounts:complete_collector_profile')}?unapproved_redirect=true")
    
    status_filter = request.GET.get('status', '')
    qs = CollectorPickup.objects.filter(collector=request.user).select_related(
        'photo_post', 'photo_post__user', 'photo_post__vendor'
    )
    
    if status_filter == 'active':
        qs = qs.filter(status__in=['assigned', 'accepted', 'in_progress'])
    elif status_filter == 'completed':
        qs = qs.filter(status='completed')
    elif status_filter == 'cancelled':
        qs = qs.filter(status='cancelled')
    
    qs = qs.order_by('-created_at')
    
    base = CollectorPickup.objects.filter(collector=request.user)
    counts = {
        'all': base.count(),
        'active': base.filter(status__in=['assigned', 'accepted', 'in_progress']).count(),
        'completed': base.filter(status='completed').count(),
        'cancelled': base.filter(status='cancelled').count(),
    }
    
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    pickups_page = paginator.get_page(page_number)
    
    return render(request, 'collector/my_pickups.html', {
        'pickups': pickups_page,
        'status_filter': status_filter,
        'counts': counts,
    })


# ── VERIFY PICKUP OTP (Step 1) ────────────────────────────────────────────────
@login_required
def verify_pickup_otp(request, pk):
    """
    Collector verifies pickup OTP.
    - Regular pickup: Client shares OTP (item is WITH client)
    - Return pickup: Vendor shares OTP (item is WITH vendor)
    """
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')

    pickup = get_object_or_404(CollectorPickup, pk=pk, collector=request.user, status__in=['assigned', 'accepted'])
    post = pickup.photo_post
    
    # Determine if this is a return pickup
    is_return = post.status == 'return_pickup_scheduled'
    is_regular = post.status == 'pickup_scheduled'
    
    if not is_return and not is_regular:
        messages.error(request, 'This pickup is no longer in the correct state.')
        return redirect('collector:my_pickups')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    error = None
    if request.method == 'POST':
        entered = request.POST.get('otp', '').strip()
        if len(entered) != 6 or not entered.isdigit():
            error = 'Please enter a valid 6-digit OTP.'
        else:
            # For return pickup, check return_pickup_otp (vendor has it)
            # For regular pickup, check pickup_otp (client has it)
            if is_return:
                correct_otp = post.return_pickup_otp
                otp_holder = 'vendor'
            else:
                correct_otp = post.pickup_otp
                otp_holder = 'client'
            
            if entered != correct_otp:
                error = f'Incorrect OTP. Ask the {otp_holder} for the correct code.'
            else:
                if is_return:
                    post.status = 'return_in_transit'
                else:
                    post.status = 'in_transit'
                post.save()
                pickup.status = 'in_progress'
                pickup.save()
                
                if is_ajax:
                    msg = 'Pickup from vendor verified! Item is now in transit.' if is_return else 'Pickup verified! Item is now in transit.'
                    return JsonResponse({'success': True, 'message': msg})
                
                if is_return:
                    messages.success(request, '✅ Pickup from vendor verified! Item is now in transit. Head to the client.')
                else:
                    messages.success(request, '✅ Pickup verified! Item is now in transit. Head to the vendor.')
                return redirect('collector:my_pickups')

        if is_ajax and error:
            return JsonResponse({'success': False, 'error': error})

    return render(request, 'collector/verify_otp.html', {
        'pickup': pickup,
        'post': post,
        'error': error,
        'step': 'pickup',
        'is_return': is_return,
        'otp_holder': 'vendor' if is_return else 'client',
    })


# ── VERIFY DELIVERY OTP (Step 2) ──────────────────────────────────────────────
@login_required
def verify_delivery_otp(request, pk):
    """
    Collector verifies delivery OTP.
    - Regular pickup: Vendor shares OTP (delivering TO vendor)
    - Return pickup: Client shares OTP (delivering TO client)
    """
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')

    pickup = get_object_or_404(CollectorPickup, pk=pk, collector=request.user, status='in_progress')
    post = pickup.photo_post
    
    # Determine if this is a return pickup
    is_return = post.status == 'return_in_transit'
    is_regular = post.status == 'in_transit'

    if not is_return and not is_regular:
        messages.error(request, 'Complete the Pickup OTP step first.')
        return redirect('collector:my_pickups')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    error = None
    if request.method == 'POST':
        entered = request.POST.get('otp', '').strip()
        if len(entered) != 6 or not entered.isdigit():
            error = 'Please enter a valid 6-digit OTP.'
        else:
            # For return pickup, check return_delivery_otp (client has it)
            # For regular pickup, check delivery_otp (vendor has it)
            if is_return:
                correct_otp = post.return_delivery_otp
                otp_holder = 'client'
            else:
                correct_otp = post.delivery_otp
                otp_holder = 'vendor'
            
            if entered != correct_otp:
                error = f'Incorrect OTP. Ask the {otp_holder} for the correct delivery code.'
            else:
                # Mark delivery complete
                if is_return:
                    post.status = 'returned_to_client'
                    post.return_collector = None  # Clear after completion
                else:
                    post.status = 'collected'
                post.save()
                
                pickup.status = 'completed'
                pickup.completed_at = timezone.now()
                pickup.payment_status = 'paid'
                pickup.save()

                # Credit earnings
                try:
                    payment = CollectorPickupPayment.objects.get(pickup=post)
                    payment.mark_as_paid()
                except CollectorPickupPayment.DoesNotExist:
                    e, _ = CollectorEarnings.objects.get_or_create(collector=request.user)
                    e.add_earning(pickup.total_payment)
                
                try:
                    # 'Receiver Pays' Logic:
                    # If return -> Client pays. Otherwise -> Vendor pays.
                    payer = post.user if is_return else post.vendor
                    if payer:
                        payer.wallet.debit(pickup.total_payment, f"Logistics Fee for {post.title}", photo_post=post)
                    
                    # Credit Collector
                    request.user.wallet.credit(pickup.total_payment, f"{post.title}", photo_post=post)
                except Exception:
                    pass

                if is_ajax:
                    msg = f'Item returned to client! ₹{pickup.total_payment} credited.' if is_return else f'Delivery confirmed! ₹{pickup.total_payment} credited.'
                    return JsonResponse({'success': True, 'message': msg})

                if is_return:
                    messages.success(request, f'✅ Item returned to client! ₹{pickup.total_payment} credited to your wallet.')
                else:
                    messages.success(request, f'✅ Delivery confirmed! ₹{pickup.total_payment} credited to your wallet.')
                return redirect('collector:my_pickups')

        if is_ajax and error:
            return JsonResponse({'success': False, 'error': error})

    return render(request, 'collector/verify_otp.html', {
        'pickup': pickup,
        'post': post,
        'error': error,
        'step': 'delivery',
        'is_return': is_return,
        'otp_holder': 'client' if is_return else 'vendor',
    })


# ── COMPLETE PICKUP (smart redirect) ─────────────────────────────────────────
@login_required
def complete_pickup(request, pk):
    """Redirect to correct OTP step based on current pickup status."""
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    pickup = get_object_or_404(CollectorPickup, pk=pk, collector=request.user)
    
    if pickup.status in ['assigned', 'accepted']:
        return redirect('collector:verify_pickup_otp', pk=pk)
    elif pickup.status == 'in_progress':
        return redirect('collector:verify_delivery_otp', pk=pk)
    else:
        messages.info(request, 'This pickup is already completed.')
        return redirect('collector:my_pickups')


# ── PICKUP DETAIL ─────────────────────────────────────────────────────────────
@login_required
def pickup_detail(request, pk):
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    pickup = get_object_or_404(CollectorPickup, pk=pk, collector=request.user)
    is_return_pickup = pickup.photo_post.status in ['return_pickup_scheduled', 'return_in_transit', 'return_requested']
    handling_fee = pickup.total_payment - pickup.base_fee - pickup.distance_fee
    
    return render(request, 'collector/pickup_detail.html', {
        'pickup': pickup,
        'item': pickup.photo_post,
        'is_return_pickup': is_return_pickup,
        'handling_fee': handling_fee
    })


@login_required
def start_trip(request, pk):
    if request.method == 'POST':
        pickup = get_object_or_404(CollectorPickup, pk=pk, collector=request.user)
        if pickup.status in ['assigned', 'accepted'] and not pickup.trip_start_at:
            pickup.trip_start_at = timezone.now()
            pickup.save()
            messages.success(request, '🚀 Trip Started! Head to the pickup location.')
        return redirect('collector:pickup_detail', pk=pk)
    return redirect('collector:my_pickups')


# ── EARNINGS ──────────────────────────────────────────────────────────────────
@login_required
def earnings(request):
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
        
    pc = request.user.profile_completion
    if pc.approval_status != 'approved':
        messages.error(request, 'Your profile must be approved to view your earnings.')
        from django.urls import reverse
        return redirect(f"{reverse('accounts:complete_collector_profile')}?unapproved_redirect=true")
    
    # Financial data from central Wallet model (source of truth)
    wallet = request.user.wallet
    total_earned = wallet.total_earned
    total_withdrawn = wallet.total_withdrawn
    
    # Get all transactions for history
    transactions_list = wallet.transactions.all().select_related('photo_post', 'photo_post__user', 'photo_post__vendor').order_by('-created_at')
    
    # Pagination: 5 transactions per page
    paginator = Paginator(transactions_list, 5)
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)
    
    current_year = timezone.now().year
    
    # Service stats
    from apps.collector.models import CollectorPickup
    pickups_count = CollectorPickup.objects.filter(collector=request.user, status='completed').count()
    avg_payout = (total_earned / pickups_count) if pickups_count > 0 else Decimal('0.00')
    
    earnings_obj, _ = CollectorEarnings.objects.get_or_create(collector=request.user)
    
    return render(request, 'collector/earnings.html', {
        'wallet': wallet,
        'earnings': earnings_obj, # Still passed for other collector-specific stats if needed
        'transactions': transactions,
        'total_earned': total_earned,
        'total_withdrawn': total_withdrawn,
        'avg_payout': avg_payout,
        'current_year': current_year,
        'completed_pickups_count': pickups_count,
    })


@login_required
def download_statement(request):
    if not request.user.is_collector:
        messages.error(request, 'Access denied.')
        return redirect('home')
        
    pc = request.user.profile_completion
    if pc.approval_status != 'approved':
        messages.error(request, 'Your profile must be approved to download statements.')
        from django.urls import reverse
        return redirect(f"{reverse('accounts:complete_collector_profile')}?unapproved_redirect=true")
    
    period = request.GET.get('period', 'all')
    try:
        user_wallet = request.user.wallet
    except:
        messages.error(request, 'Wallet not found.')
        return redirect('collector:earnings')
        
    transactions = Transaction.objects.filter(wallet=user_wallet).order_by('-created_at')

    # Apply filters
    now = timezone.now()
    date_display = period.upper()
    
    if period == 'week':
        transactions = transactions.filter(created_at__gte=now - timedelta(days=7))
    elif period == 'month':
        transactions = transactions.filter(created_at__gte=now - timedelta(days=30))
    elif period == 'custom':
        start_str = request.GET.get('start_date')
        end_str = request.GET.get('end_date')
        if start_str and end_str:
            try:
                from datetime import datetime
                start_date = timezone.make_aware(datetime.strptime(start_str, '%Y-%m-%d'))
                end_date = timezone.make_aware(datetime.strptime(end_str, '%Y-%m-%d')).replace(hour=23, minute=59, second=59)
                transactions = transactions.filter(created_at__range=(start_date, end_date))
                date_display = f"{start_str} TO {end_str}"
            except Exception:
                pass

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        PRIMARY = colors.HexColor('#17cf17')
        DARK = colors.HexColor('#1e293b')
        GRAY = colors.HexColor('#64748b')
        LIGHT_BG = colors.HexColor('#f8fafc')

        def get_style(name, **kwargs):
            style_kwargs = {'fontName': 'Helvetica', 'fontSize': 10}
            style_kwargs.update(kwargs)
            return ParagraphStyle(name, **style_kwargs)

        story = []
        
        # --- LETTERHEAD ---
        story.append(Paragraph('<font color="#17cf17"><b>E-RECYCLO</b></font>', get_style('brand', fontSize=28, alignment=TA_LEFT)))
        story.append(Paragraph('Collector Digital Wallet & Service Earnings', get_style('tag', fontSize=9, textColor=GRAY)))
        story.append(Spacer(1, 0.2*cm))
        story.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=10))
        
        # --- STATEMENT HEADER ---
        story.append(Paragraph('COLLECTOR EARNINGS STATEMENT', get_style('title', fontSize=16, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=10)))
        
        # --- CUSTOMER & ACCOUNT INFO ---
        info_data = [
            [Paragraph(f'<b>Name:</b> {request.user.get_full_name() or request.user.email}', get_style('info')), 
             Paragraph(f'<b>Statement Period:</b> {date_display}', get_style('info'))],
            [Paragraph(f'<b>Collector ID:</b> #{request.user.pk}', get_style('info')), 
             Paragraph(f'<b>Generation Date:</b> {now.strftime("%d %b, %Y")}', get_style('info'))],
            [Paragraph(f'<b>Wallet Status:</b> ACTIVE', get_style('info')), 
             Paragraph(f'<b>Current Balance:</b> Rs. {user_wallet.balance}', get_style('info', fontName='Helvetica-Bold', textColor=PRIMARY))]
        ]
        info_table = Table(info_data, colWidths=[9*cm, 9*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.8*cm))
        
        # --- TRANSACTION TABLE ---
        story.append(Paragraph('TRANSACTION LOGS', get_style('logtitle', fontSize=11, fontName='Helvetica-Bold', textColor=PRIMARY, spaceAfter=6)))
        
        headers = [
            Paragraph('<b>DATE</b>', get_style('th', textColor=colors.white)),
            Paragraph('<b>DESCRIPTION</b>', get_style('th', textColor=colors.white)),
            Paragraph('<b>TYPE</b>', get_style('th', textColor=colors.white)),
            Paragraph('<b>AMOUNT</b>', get_style('th', textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph('<b>BALANCE</b>', get_style('th', textColor=colors.white, alignment=TA_RIGHT))
        ]
        
        table_data = [headers]
        for txn in transactions:
            # Clean up description to show product name only
            desc = txn.description
            if txn.photo_post:
                desc = txn.photo_post.title
            else:
                # Fallback cleaning
                for prefix in ["Product Value: ", "Trip Payout: ", "Pickup delivered: ", "Offer accepted: "]:
                    desc = desc.replace(prefix, "")

            row = [
                txn.created_at.strftime('%d/%m/%y'),
                Paragraph(desc[:50], get_style('td', fontSize=9)),
                txn.transaction_type.upper(),
                Paragraph(f'{"-" if txn.transaction_type == "debit" else "+"} Rs. {txn.amount}', 
                         get_style('td', fontSize=9, alignment=TA_RIGHT, textColor=colors.red if txn.transaction_type == 'debit' else colors.black)),
                Paragraph(f'Rs. {txn.balance_after}', get_style('td', fontSize=9, alignment=TA_RIGHT))
            ]
            table_data.append(row)
            
        if not transactions.exists():
            table_data.append(['', Paragraph('No transactions found for this period', get_style('td', alignment=TA_CENTER)), '', '', ''])

        t = Table(table_data, colWidths=[2.5*cm, 7.5*cm, 2*cm, 3*cm, 3*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), DARK),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('GRID', (0,0), (-1,-1), 0.1, colors.lightgrey),
        ]))
        story.append(t)
        
        # --- FOOTER ---
        story.append(Spacer(1, 2*cm))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.lightgrey, spaceAfter=6))
        story.append(Paragraph('This is a computer-generated statement and does not require a physical signature.', 
                             get_style('ft', fontSize=8, alignment=TA_CENTER, textColor=GRAY)))
        story.append(Paragraph('E-RECYCLO Platform | Collector Services Division', 
                             get_style('ft', fontSize=8, alignment=TA_CENTER, textColor=GRAY)))

        doc.build(story); buf.seek(0)
        return FileResponse(buf, as_attachment=True, filename=f'erecyclo_collector_statement_{period}_{now.strftime("%Y%m%d")}.pdf')

    except Exception as e:
        messages.error(request, f'Could not generate statement: {str(e)}')
        return redirect('collector:earnings')