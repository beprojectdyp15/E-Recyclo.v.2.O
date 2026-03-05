"""Vendor views for E-RECYCLO - Updated with 5km radius visibility"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
import math

from apps.client.models import PhotoPost, EvaluationHistory
from apps.accounts.models import Account
from .forms import AcceptItemForm, RejectItemForm
from .models import VendorAssignment, VendorReport


ALL_ACCEPTED = [
    'accepted','pickup_scheduled','in_transit','collected','under_review',
    'return_requested','return_pickup_scheduled','return_in_transit',
    'returned_to_client','completed',
]

# Vehicle capacity mapping for collector assignment
VEHICLE_CAPACITY = {
    'bike': ['small', 'medium'],
    'scooter': ['small', 'medium'],
    'auto': ['small', 'medium', 'large'],
    'van': ['small', 'medium', 'large', 'very_large'],
    'tempo': ['small', 'medium', 'large', 'very_large'],
    'pickup': ['small', 'medium', 'large', 'very_large'],
}


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula (returns km)"""
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def get_nearby_vendors(post, radius_km=5):
    """Get all approved vendors within radius of the post location"""
    vendors = Account.objects.filter(
        is_vendor=True,
        is_active=True,
        profile_completion__approval_status='approved'
    )
    nearby = []
    for vendor in vendors:
        try:
            vp = vendor.vendor_profile
            if vp.latitude and vp.longitude:
                dist = calculate_distance(post.latitude, post.longitude, vp.latitude, vp.longitude)
                if dist <= radius_km:
                    nearby.append({'vendor': vendor, 'distance': dist})
        except:
            continue
    return sorted(nearby, key=lambda x: x['distance'])


def get_nearby_collectors(post, radius_km=5):
    """Get all approved collectors within radius who can handle the item size"""
    collectors = Account.objects.filter(
        is_collector=True,
        is_active=True,
        profile_completion__approval_status='approved'
    )
    
    # Determine required vehicle capacity based on item size
    item_size = post.item_size or 'medium'  # Default to medium if not specified
    
    nearby = []
    for collector in collectors:
        try:
            cp = collector.collector_profile
            if cp.latitude and cp.longitude:
                dist = calculate_distance(post.latitude, post.longitude, cp.latitude, cp.longitude)
                if dist <= radius_km:
                    # Check if collector's vehicle can handle the item
                    vehicle_type = cp.vehicle_type or 'bike'
                    can_handle = item_size in VEHICLE_CAPACITY.get(vehicle_type, ['small', 'medium'])
                    
                    # Check if collector is not already busy with an active pickup
                    is_busy = PhotoPost.objects.filter(
                        collector=collector,
                        status__in=['pickup_scheduled', 'in_transit']
                    ).exists()
                    
                    # Add to list - mark if can handle or not
                    if not is_busy:
                        nearby.append({
                            'collector': collector,
                            'distance': dist,
                            'vehicle_type': vehicle_type,
                            'can_handle': can_handle
                        })
        except:
            continue
    
    # Sort by: can_handle first, then by distance
    nearby.sort(key=lambda x: (not x['can_handle'], x['distance']))
    return nearby


@login_required
def dashboard(request):
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    pc = request.user.profile_completion
    if pc.approval_status != 'approved':
        messages.warning(request, 'Your profile is pending approval.')
    
    # Get vendor's location for nearby items
    try:
        vp = request.user.vendor_profile
        vendor_lat, vendor_lon = vp.latitude, vp.longitude
    except:
        vendor_lat, vendor_lon = None, None
    
    # Count pending items visible to this vendor (within 5km, status=pending)
    pending_count = 0
    if vendor_lat and vendor_lon:
        pending_items = PhotoPost.objects.filter(status='pending')
        for item in pending_items:
            dist = calculate_distance(item.latitude, item.longitude, vendor_lat, vendor_lon)
            if dist <= 5:
                pending_count += 1
    
    # Count items needing re-evaluation (Must have been evaluated BY THIS VENDOR before)
    from apps.client.models import EvaluationHistory
    base_collected = PhotoPost.objects.filter(vendor=request.user, status='collected')
    reeval_count = 0
    for item in base_collected:
        if EvaluationHistory.objects.filter(post=item, vendor=request.user).exists():
            reeval_count += 1
    
    return render(request, 'vendor/dashboard.html', {
        'pending_requests': pending_count,
        'accepted_items': PhotoPost.objects.filter(vendor=request.user, status__in=ALL_ACCEPTED).count(),
        'completed_items_count': PhotoPost.objects.filter(vendor=request.user, status='completed').count(),
        'total_value': PhotoPost.objects.filter(vendor=request.user, status='completed').aggregate(t=Sum('vendor_final_value'))['t'] or Decimal('0.00'),
        'recent_requests': PhotoPost.objects.filter(vendor=request.user).order_by('-created_at')[:5],
        'profile_completion': pc,
        'reeval_count': reeval_count,
    })


@login_required
def pending_requests(request):
    """Show all pending items within 5km of vendor's location.
    Excludes items that this vendor previously had and declined re-evaluation.
    """
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    try:
        vp = request.user.vendor_profile
        vendor_lat, vendor_lon = vp.latitude, vp.longitude
    except:
        messages.error(request, 'Please complete your profile with location.')
        return redirect('accounts:complete_vendor_profile')
    
    if not vendor_lat or not vendor_lon:
        messages.error(request, 'Please add your business location to see nearby requests.')
        return redirect('accounts:complete_vendor_profile')
    
    # Get all pending items within 5km
    # Exclude items where this vendor previously had and declined (check EvaluationHistory)
    all_pending = PhotoPost.objects.filter(status='pending').order_by('-created_at')
    nearby_items = []
    
    for item in all_pending:
        # Check if this vendor previously evaluated this item (means client transferred away)
        from apps.client.models import EvaluationHistory
        was_previous_vendor = EvaluationHistory.objects.filter(
            post=item, 
            vendor=request.user
        ).exists()
        
        if was_previous_vendor:
            # This vendor already had this item - skip it
            continue
        
        dist = calculate_distance(item.latitude, item.longitude, vendor_lat, vendor_lon)
        if dist <= 5:
            nearby_items.append({
                'item': item,
                'distance': round(dist, 2)
            })
    
    from django.core.paginator import Paginator
    paginator = Paginator(nearby_items, 10)
    page_number = request.GET.get('page')
    requests_page = paginator.get_page(page_number)
    
    return render(request, 'vendor/pending_requests.html', {
        'requests': requests_page,
        'total_count': len(nearby_items)
    })


@login_required  
def accept_item(request, pk):
    """Vendor accepts an item - it becomes available for collectors to claim.
    If this is a transfer from another vendor, we track the previous vendor and reset for fresh start.
    """
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Handle race condition - item might not exist or be taken
    try:
        item = PhotoPost.objects.get(pk=pk)
    except PhotoPost.DoesNotExist:
        messages.warning(request, '😕 This item no longer exists.')
        return redirect('vendor:pending_requests')
    
    if item.status != 'pending':
        messages.warning(request, '⚡ Oops! This item was just accepted by another vendor.')
        return redirect('vendor:pending_requests')
    
    try:
        vp = request.user.vendor_profile
        dist = calculate_distance(item.latitude, item.longitude, vp.latitude, vp.longitude)
        if dist > 5:
            messages.error(request, 'This item is outside your service area.')
            return redirect('vendor:pending_requests')
    except:
        messages.error(request, 'Please complete your profile.')
        return redirect('vendor:pending_requests')
    
    # Check if this is a transfer from another vendor (has evaluation history)
    from apps.client.models import EvaluationHistory
    previous_evaluation = EvaluationHistory.objects.filter(post=item).order_by('-evaluated_at').first()
    is_vendor_transfer = previous_evaluation is not None and previous_evaluation.vendor is not None
    previous_vendor = previous_evaluation.vendor if is_vendor_transfer else None
    
    if request.method == 'POST':
        # Double-check (same user, different tab)
        item.refresh_from_db()
        if item.status != 'pending':
            messages.warning(request, '⚡ This item was just accepted (possibly by you in another tab).')
            return redirect('vendor:pending_requests')
        
        item.vendor = request.user
        item.assigned_at = timezone.now()
        item.status = 'pickup_scheduled'
        
        # DON'T generate OTPs here - they will be generated when collector accepts
        # The model's save() method handles this when collector_id is set
        
        # For vendor transfers, store the previous vendor ID AND reset for fresh start
        if is_vendor_transfer and previous_vendor:
            item.vendor_remarks = f"TRANSFER_FROM_VENDOR:{previous_vendor.pk}"
            # FRESH START for new vendor - reset ALL evaluation-related fields
            # This ensures new vendor sees it as a new evaluation, not re-evaluation
            item.rejection_count = 0
            item.offer_count = 0  # Reset offer count for fresh start
            # Clear previous evaluation data
            item.vendor_final_value = None
            item.evaluation_type = ''
            item.eco_points_awarded = 0
            item.condition_notes = ''
            item.price_breakdown = ''
            item.evaluation_date = None
            item.vendor_declined_reevaluation = False
            # Clear collector so new collector can be assigned
            item.collector = None
            item.pickup_otp = ''
            item.delivery_otp = ''
        
        item.save()
        
        if is_vendor_transfer and previous_vendor:
            messages.success(request, f'✅ Transfer accepted! Collectors will pick up from {previous_vendor.get_full_name()} and deliver to you.')
        else:
            nearby_collectors = get_nearby_collectors(item, radius_km=5)
            suitable = [c for c in nearby_collectors if c.get('can_handle', True)]
            
            if suitable:
                messages.success(request, f'✅ Accepted! {len(suitable)} collector(s) nearby can see this pickup.')
            else:
                messages.success(request, '✅ Accepted! Pickup will be visible when collectors come online.')
        
        return redirect('vendor:accepted_items')
    
    return render(request, 'vendor/accept_item.html', {
        'item': item,
        'is_vendor_transfer': is_vendor_transfer,
        'previous_vendor': previous_vendor,
    })


@login_required
def reject_item(request, pk):
    """Vendor rejects an item - it stays available for other vendors"""
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Item must be pending (for initial rejection) or assigned to this vendor
    item = PhotoPost.objects.filter(pk=pk).first()
    if not item:
        messages.error(request, 'Item not found.')
        return redirect('vendor:pending_requests')
    
    # If item is assigned to this vendor, allow rejection
    if item.status == 'assigned' and item.vendor == request.user:
        pass
    # If item is pending, any nearby vendor can "pass" on it (just don't accept)
    elif item.status == 'pending':
        pass
    else:
        messages.error(request, 'Cannot reject this item.')
        return redirect('vendor:pending_requests')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for rejection.')
            return render(request, 'vendor/reject_item.html', {'post': item})
        
        # If was assigned to this vendor, reset to pending
        if item.vendor == request.user:
            item.vendor = None
            item.assigned_at = None
        
        item.status = 'pending'
        item.vendor_remarks = f"Rejected by vendor: {reason}"
        item.save()
        
        messages.success(request, 'Item rejected. It will be available for other vendors.')
        return redirect('vendor:pending_requests')
    
    return render(request, 'vendor/reject_item.html', {'post': item})


@login_required
def evaluate_item(request, pk):
    """First eval or re-eval after client rejection. History always saved."""
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Allow evaluation of collected items OR items sent back for re-evaluation
    item = get_object_or_404(PhotoPost, pk=pk, vendor=request.user)
    
    if item.status not in ['collected', 'under_review']:
        messages.error(request, 'This item cannot be evaluated yet.')
        return redirect('vendor:accepted_items')
    
    # ONLY show THIS vendor's history (not previous vendors' offers)
    history = EvaluationHistory.objects.filter(post=item, vendor=request.user).order_by('-evaluated_at')
    previous_offer = history.first()

    if request.method == 'POST':
        # Synchronization check - refresh and verify status
        item.refresh_from_db()
        if item.status != 'collected':
            messages.warning(request, '⚡ This item was just evaluated (possibly by you in another tab).')
            return redirect('vendor:accepted_items')
        
        evaluation_type = request.POST.get('evaluation_type', '').strip()
        try:
            new_value = Decimal(request.POST.get('vendor_final_value', '0') or '0')
        except Exception:
            new_value = Decimal('0')
        eco_points = int(request.POST.get('eco_points', '0') or '0')
        vendor_remarks = request.POST.get('vendor_remarks', '').strip()
        condition_notes = request.POST.get('condition_notes', '').strip()
        price_breakdown = request.POST.get('price_breakdown', '').strip()

        ctx = {'item': item, 'history': history, 'previous_offer': previous_offer}
        
        if not evaluation_type:
            messages.error(request, 'Please select an evaluation type.')
            return render(request, 'vendor/evaluate_item.html', ctx)
        if not vendor_remarks:
            messages.error(request, 'Please provide your assessment notes.')
            return render(request, 'vendor/evaluate_item.html', ctx)

        # Enforce: re-eval must be >= previous offer
        if previous_offer and previous_offer.vendor_final_value is not None:
            if new_value < previous_offer.vendor_final_value:
                messages.error(request, f'New offer ₹{new_value} must be ≥ previous offer ₹{previous_offer.vendor_final_value}.')
                return render(request, 'vendor/evaluate_item.html', ctx)

        # Save to history
        EvaluationHistory.objects.create(
            post=item, vendor=request.user,
            evaluation_type=evaluation_type, vendor_final_value=new_value,
            eco_points_awarded=eco_points, vendor_remarks=vendor_remarks,
            condition_notes=condition_notes, price_breakdown=price_breakdown,
        )
        
        item.evaluation_type = evaluation_type
        item.vendor_final_value = new_value
        item.eco_points_awarded = eco_points
        item.vendor_remarks = vendor_remarks
        item.condition_notes = condition_notes
        item.price_breakdown = price_breakdown
        item.status = 'under_review'
        item.evaluation_date = timezone.now()
        item.offer_count = (item.offer_count or 0) + 1
        item.vendor_declined_reevaluation = False
        item.save()
        
        messages.success(request, f'Offer #{item.offer_count} of ₹{new_value} sent to client.')
        return redirect('vendor:accepted_items')

    return render(request, 'vendor/evaluate_item.html', {
        'item': item, 'history': history, 'previous_offer': previous_offer,
    })


@login_required
def decline_reevaluation(request, pk):
    """Vendor declines to re-evaluate. Client chooses: accept last offer, return, or transfer."""
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    item = get_object_or_404(PhotoPost, pk=pk, vendor=request.user, status='collected')
    
    # Must have rejection_count > 0 to decline re-evaluation
    if item.rejection_count == 0:
        messages.error(request, 'Cannot decline re-evaluation for items without prior offer rejection.')
        return redirect('vendor:accepted_items')
    
    # Get last offer to show in template and preserve values
    # ONLY show this vendor's own history
    history = EvaluationHistory.objects.filter(post=item, vendor=request.user).order_by('-evaluated_at')
    last_offer = history.first()
    
    # Context to pass to template
    ctx = {
        'item': item, 
        'last_offer': last_offer,
        'history': history
    }
    
    if request.method == 'POST':
        # Sync check
        item.refresh_from_db()
        if item.status != 'collected':
            messages.warning(request, '⚡ Item status has changed.')
            return redirect('vendor:accepted_items')
        
        item.vendor_declined_reevaluation = True
        item.vendor_remarks = request.POST.get('decline_reason', '').strip() or 'Vendor declined re-evaluation.'
        
        # Preserve the last offer values so client can accept them
        if last_offer:
            EvaluationHistory.objects.create(
                post=item, vendor=request.user,
                evaluation_type=last_offer.evaluation_type,
                vendor_final_value=last_offer.vendor_final_value,
                eco_points_awarded=last_offer.eco_points_awarded,
                vendor_remarks=item.vendor_remarks,
                condition_notes=last_offer.condition_notes,
                price_breakdown=last_offer.price_breakdown,
            )
            item.vendor_final_value = last_offer.vendor_final_value
            item.eco_points_awarded = last_offer.eco_points_awarded
            item.evaluation_type = last_offer.evaluation_type
        
        item.save()
        messages.success(request, 'Decline recorded. Client can accept last offer, request return, or transfer to another vendor.')
        return redirect('vendor:accepted_items')
    
    return render(request, 'vendor/decline_reevaluation.html', ctx)


@login_required
def accepted_items(request):
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    tab = request.GET.get('tab', 'all')
    
    # Items where this vendor is currently assigned
    base = PhotoPost.objects.filter(vendor=request.user)
    
    # Get items that were transferred FROM this vendor to another vendor
    from apps.client.models import EvaluationHistory
    prev_evaluated_ids = EvaluationHistory.objects.filter(
        vendor=request.user
    ).values_list('post_id', flat=True).distinct()
    
    # Items that this vendor previously had but are now with another vendor
    transferred_items = PhotoPost.objects.filter(
        pk__in=prev_evaluated_ids
    ).exclude(
        vendor=request.user
    ).exclude(
        status='rejected'
    )
    
    # Get IDs of items that THIS vendor has evaluated before (to distinguish re-evals)
    my_eval_ids = set(EvaluationHistory.objects.filter(
        vendor=request.user
    ).values_list('post_id', flat=True))

    if tab == 'collector_assigned':
        items = base.filter(status__in=['pickup_scheduled', 'in_transit']).order_by('-created_at')
    elif tab == 'received':
        items_pks = [i.pk for i in base.filter(status='collected') if i.pk not in my_eval_ids]
        items = PhotoPost.objects.filter(pk__in=items_pks).order_by('-created_at')
    elif tab == 'reevaluation':
        items_pks = [i.pk for i in base.filter(status='collected') if i.pk in my_eval_ids]
        items = PhotoPost.objects.filter(pk__in=items_pks).order_by('-created_at')
    elif tab == 'under_review':
        items = base.filter(status='under_review').order_by('-evaluation_date')
    elif tab == 'completed':
        items = base.filter(status='completed').order_by('-completed_at')
    elif tab == 'returns':
        items = base.filter(status__in=['return_requested', 'return_pickup_scheduled', 'return_in_transit', 'returned_to_client']).order_by('-created_at')
    elif tab == 'transferred':
        items = transferred_items.order_by('-created_at')
    else:
        tab = 'all'
        current_items = base.exclude(status__in=['pending', 'rejected'])
        all_item_ids = list(current_items.values_list('pk', flat=True)) + list(transferred_items.values_list('pk', flat=True))
        items = PhotoPost.objects.filter(pk__in=all_item_ids).order_by('-created_at')

    from django.core.paginator import Paginator
    paginator = Paginator(items, 10)
    page_number = request.GET.get('page')
    items_page = paginator.get_page(page_number)

    # Re-wrap list into queryset if needed, but for now we'll handle list in counts
    collected_items = base.filter(status='collected')
    received_count = 0
    reeval_count = 0
    for i in collected_items:
        if i.pk in my_eval_ids: reeval_count += 1
        else: received_count += 1
    
    current_count = base.exclude(status__in=['pending', 'rejected']).count()
    transferred_count = transferred_items.count()
    transferred_ids = list(transferred_items.values_list('pk', flat=True))

    counts = {
        'all': current_count + transferred_count,
        'collector_assigned': base.filter(status__in=['pickup_scheduled', 'in_transit']).count(),
        'received': received_count,
        'reevaluation': reeval_count,
        'under_review': base.filter(status='under_review').count(),
        'completed': base.filter(status='completed').count(),
        'returns': base.filter(status__in=['return_requested', 'return_pickup_scheduled', 'return_in_transit', 'returned_to_client']).count(),
        'transferred': transferred_count,
    }
    
    # Pass transferred item IDs and set attribute on objects for template convenience
    for item in items_page:
        item.is_transferred = item.pk in transferred_ids or tab == 'transferred'
        item.has_evaluated_by_me = item.pk in my_eval_ids
    
    return render(request, 'vendor/accepted_items.html', {
        'items': items_page, 
        'tab': tab, 
        'counts': counts, 
        'is_transferred_tab': tab == 'transferred',
        'transferred_ids': transferred_ids,
    })


@login_required
def item_detail(request, pk):
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    from apps.collector.models import CollectorPickup
    
    post = get_object_or_404(PhotoPost, pk=pk)
    
    # Check if this vendor has access (current or previous vendor)
    is_current_vendor = post.vendor == request.user
    
    # Get ALL history to check access
    all_history = EvaluationHistory.objects.filter(post=post).order_by('evaluated_at')
    was_previous_vendor = all_history.filter(vendor=request.user).exists()
    
    if not is_current_vendor and not was_previous_vendor:
        messages.error(request, 'Access denied.')
        return redirect('vendor:accepted_items')
    
    # Build vendor-wise history (Fixed repetition issue)
    vendor_history = []
    seen_vids = set()
    ordered_vids = []
    
    # Extract unique vendors in chronological order of evaluation
    for eh in all_history:
        if eh.vendor_id and eh.vendor_id not in seen_vids:
            seen_vids.add(eh.vendor_id)
            ordered_vids.append(eh.vendor_id)
    
    # Ensure current vendor is included if they haven't evaluated yet
    if post.vendor_id and post.vendor_id not in seen_vids:
        ordered_vids.append(post.vendor_id)

    # Find the logged-in user's position in the vendor sequence
    my_sequence_index = 0
    for idx, vid in enumerate(ordered_vids, 1):
        if vid == request.user.pk:
            my_sequence_index = idx
            break

    for i, vendor_id in enumerate(ordered_vids, 1):
        try:
            vendor = Account.objects.get(pk=vendor_id)
        except Account.DoesNotExist:
            continue
        
        vendor_evals = all_history.filter(vendor_id=vendor_id).order_by('evaluated_at')
        is_this_vendor = vendor_id == request.user.pk
        is_vendor_current = post.vendor and post.vendor.pk == vendor_id
        
        total_offers = vendor_evals.count()
        rejected_offers = vendor_evals.filter(rejected_by_client=True).count()
        accepted_offer = vendor_evals.filter(rejected_by_client=False).last()
        
        if is_vendor_current:
            if post.status == 'completed':
                final_status = 'completed'
            elif post.status == 'returned_to_client':
                final_status = 'returned'
            else:
                final_status = 'active'
        else:
            final_status = 'transferred'
        
        # Privacy Logic: View own records + all past records. 
        # Current vendor sees everything. Previous vendors can't see future transfers.
        can_view_evals = is_current_vendor or (i <= my_sequence_index)
        
        vendor_history.append({
            'order': i,
            'vendor': vendor,
            'is_this_vendor': is_this_vendor,
            'is_current': is_vendor_current,
            'evaluations': vendor_evals,
            'total_offers': total_offers,
            'rejected_offers': rejected_offers,
            'accepted_offer': accepted_offer,
            'final_status': final_status,
            'can_view_evaluations': can_view_evals,
        })
    
    # Reverse for UI (Match client's upload_detail: Newest at top)
    vendor_history.reverse()
    
    # Build Collector History (Synchronized with client view)
    collector_history = []
    pickups = CollectorPickup.objects.filter(photo_post=post).select_related('collector').order_by('created_at')
    
    # We need vendors in chronological order to determine transfer addresses
    unique_vids = []
    for vid in all_history.values_list('vendor_id', flat=True):
        if vid and vid not in unique_vids:
            unique_vids.append(vid)
    if post.vendor_id and post.vendor_id not in unique_vids:
        unique_vids.append(post.vendor_id)

    vendor_objs = []
    for vid in unique_vids:
        try:
            v = Account.objects.get(pk=vid)
            vendor_objs.append(v)
        except: continue

    for i, p in enumerate(pickups, 1):
        c_type = "Primary Pickup"
        pickup_name = "Pickup From Client"
        pickup_addr = post.address
        pickup_coords = {'lat': post.latitude, 'long': post.longitude}
        delivery_name = "Deliver To Vendor"
        delivery_addr = "N/A"
        delivery_coords = {'lat': 0, 'long': 0}
        
        is_return = False
        if post.status in ['return_requested', 'return_pickup_scheduled', 'return_in_transit', 'returned_to_client'] and i == len(pickups) and i > 1:
            is_return = True
        elif post.return_collector and p.collector == post.return_collector:
            is_return = True

        if is_return:
            c_type = "Return Shipment"
            if post.vendor and hasattr(post.vendor, 'vendor_profile'):
                pickup_name = "Pickup From Vendor"
                pickup_addr = post.vendor.vendor_profile.business_address
                pickup_coords = {'lat': post.vendor.vendor_profile.latitude, 'long': post.vendor.vendor_profile.longitude}
            else:
                pickup_name = "Pickup From Vendor"
                pickup_addr = "Vendor Facility"
            delivery_name = "Deliver To Client"
            delivery_addr = post.address
            delivery_coords = {'lat': post.latitude, 'long': post.longitude}
        elif i > 1:
            c_type = "Transfer Shipment"
            try:
                prev_v = vendor_objs[i-2]
                curr_v = vendor_objs[i-1]
                pickup_name = "Pickup From Previous Vendor"
                pickup_addr = prev_v.vendor_profile.business_address
                pickup_coords = {'lat': prev_v.vendor_profile.latitude, 'long': prev_v.vendor_profile.longitude}
                delivery_name = "Deliver To New Vendor"
                delivery_addr = curr_v.vendor_profile.business_address
                delivery_coords = {'lat': curr_v.vendor_profile.latitude, 'long': curr_v.vendor_profile.longitude}
            except:
                pickup_name = "Pickup From Previous Vendor"
                pickup_addr = "Previous Facility Unknown"
                delivery_name = "Deliver To New Vendor"
                delivery_addr = "New Facility Unknown"
        else:
            target_v = vendor_objs[0] if vendor_objs else post.vendor
            if target_v and hasattr(target_v, 'vendor_profile'):
                delivery_name = "Deliver To Vendor"
                delivery_addr = target_v.vendor_profile.business_address
                delivery_coords = {'lat': target_v.vendor_profile.latitude, 'long': target_v.vendor_profile.longitude}

        collector_history.append({
            'order': i,
            'collector': p.collector,
            'status': p.get_status_display(),
            'type': c_type,
            'pickup_name': pickup_name,
            'pickup_address': pickup_addr,
            'pickup_lat': pickup_coords['lat'],
            'pickup_long': pickup_coords['long'],
            'delivery_name': delivery_name,
            'delivery_address': delivery_addr,
            'delivery_lat': delivery_coords['lat'],
            'delivery_long': delivery_coords['long'],
            'date': p.completed_at or p.created_at,
            'is_completed': p.status == 'completed'
        })
    collector_history.reverse()

    # Get this vendor's stats
    my_history = all_history.filter(vendor=request.user).order_by('evaluated_at')
    total_offers = my_history.count()
    rejected_offers = my_history.filter(rejected_by_client=True).count()
    accepted_offer = my_history.filter(rejected_by_client=False).last()
    
    # Determine transaction status for this vendor
    if is_current_vendor:
        if post.status == 'completed':
            transaction_status = 'completed'
        elif post.status == 'returned_to_client':
            transaction_status = 'returned'
        elif post.vendor_declined_reevaluation:
            transaction_status = 'declined'
        else:
            transaction_status = 'active'
    else:
        transaction_status = 'transferred'

    s = post.status
    context = {
        'post': post, 
        'history': my_history,
        'vendor_history': vendor_history,
        'collector_history': collector_history,
        'is_current_vendor': is_current_vendor,
        'was_previous_vendor': was_previous_vendor and not is_current_vendor,
        'total_offers': total_offers,
        'rejected_offers': rejected_offers,
        'accepted_offer': accepted_offer,
        'transaction_status': transaction_status,
        'collector_status_tag': (
            "Delivered" if s in ['collected', 'under_review', 'completed']
            else "Searching" if s in ['assigned', 'accepted', 'pickup_scheduled'] and not post.collector
            else "Scheduled" if s in ['assigned', 'accepted', 'pickup_scheduled']
            else "Searching" if s == 'return_requested' and not post.return_collector
            else "Scheduled" if s == 'return_pickup_scheduled'
            else "In Transit" if s in ['in_transit', 'return_in_transit']
            else "Returned" if s == 'returned_to_client'
            else "Pending"
        ),
    }

    # Generate Situational Description for Vendor (CTC)
    status_msg = "Item is being processed."
    
    if not is_current_vendor:
        # Perspective of a previous vendor during the transfer process
        if s in ['assigned', 'accepted']:
            status_msg = "Client requested transfer, looking for nearby collector."
        elif s == 'pickup_scheduled':
            if post.collector:
                status_msg = "Pickup is scheduled. Exchange OTP along with item for transfer."
            else:
                status_msg = "New vendor has accepted your transfer and now looking for collector."
        elif s == 'in_transit':
            status_msg = "Collector is in-transit to transfer your item to new vendor."
        elif s in ['collected', 'under_review', 'completed', 'returned_to_client']:
            status_msg = "Transferred to new vendor. You have no more access to the item."
        else:
            status_msg = "Transferred to another facility."
    else:
        # Perspective of the currently assigned vendor
        is_transfer_proc = len(ordered_vids) > 1
        
        if s == 'assigned': 
            status_msg = "You have been assigned this item. We are now arranging a collector for pickup." if not is_transfer_proc else "You have been assigned this item. We are now arranging a transfer from the previous vendor."
        elif s == 'accepted': 
            status_msg = "Assignment confirmed. A logistics partner is being matched for pickup." if not is_transfer_proc else "Assignment confirmed. Arranging a collector to pick up the item from the previous vendor."
        elif s == 'pickup_scheduled':
            if post.collector:
                if is_transfer_proc:
                    status_msg = "Transfer scheduled. The assigned collector is en-route to pick up the item from the previous vendor's facility."
                else:
                    status_msg = "Pickup scheduled. The assigned collector is en-route to the client address."
            else:
                status_msg = "Recycling request accepted. Searching for a nearby collector to initiate pickup."
        elif s == 'in_transit': 
            status_msg = "The item is safely in transit and heading to your facility for technical inspection."
        elif s == 'collected':
            if post.vendor_declined_reevaluation:
                status_msg = "You have declined the re-evaluation request. Awaiting client's choice to accept the last offer or request a return."
            elif total_offers > 0:
                status_msg = "Re-evaluation requested! Please review the client's expected price and remarks to provide a revised offer."
            else:
                status_msg = "Item delivered! Please perform a deep technical inspection and provide your official evaluation offer."
        elif s == 'under_review':
            status_msg = "Your evaluation offer has been sent to the client. You will be notified once they accept or request adjustments."
        elif s == 'return_requested': status_msg = "Client requested a return. We are matching a collector to return the item from your facility."
        elif s == 'return_pickup_scheduled': status_msg = "A collector is en-route to your facility to pick up the item for client return."
        elif s == 'return_in_transit': status_msg = "The item has been picked up from your facility and is being delivered back to the client."
        elif s == 'returned_to_client': status_msg = "The item has been successfully returned to the client's registered address."
        elif s == 'completed': status_msg = "Process complete! The item has been successfully recycled. Transaction logs are now finalized."
        elif s == 'rejected': status_msg = "This request was canceled or rejected."

    context['status_msg'] = status_msg
    return render(request, 'vendor/item_detail.html', context)


@login_required
def reports(request):
    if not request.user.is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    yr = timezone.now().year
    monthly_stats = []
    for m in range(1, 13):
        s = PhotoPost.objects.filter(
            vendor=request.user, status='completed',
            completed_at__year=yr, completed_at__month=m
        ).aggregate(count=Count('id'), value=Sum('vendor_final_value'))
        monthly_stats.append({
            'month': m,
            'count': s['count'] or 0,
            'value': s['value'] or Decimal('0.00')
        })
    
    base = PhotoPost.objects.filter(vendor=request.user)
    
    return render(request, 'vendor/reports.html', {
        'monthly_stats': monthly_stats,
        'total_accepted': base.filter(status__in=ALL_ACCEPTED).count(),
        'total_rejected': base.filter(status='rejected').count(),
        'total_revenue': base.filter(status='completed').aggregate(t=Sum('vendor_final_value'))['t'] or Decimal('0.00'),
        'current_year': yr,
    })