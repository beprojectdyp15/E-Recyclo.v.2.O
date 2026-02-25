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
    
    # Count items needing re-evaluation
    reeval_count = PhotoPost.objects.filter(
        vendor=request.user,
        status='collected',
        rejection_count__gt=0
    ).count()
    
    return render(request, 'vendor/dashboard.html', {
        'pending_requests': pending_count,
        'accepted_items': PhotoPost.objects.filter(vendor=request.user, status__in=ALL_ACCEPTED).count(),
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
    
    return render(request, 'vendor/pending_requests.html', {
        'requests': nearby_items,
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
    history = EvaluationHistory.objects.filter(post=item).order_by('-evaluated_at')
    last_offer = history.first()
    
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
            item.vendor_final_value = last_offer.vendor_final_value
            item.eco_points_awarded = last_offer.eco_points_awarded
            item.evaluation_type = last_offer.evaluation_type
        
        item.save()
        messages.success(request, 'Decline recorded. Client can accept last offer, request return, or transfer to another vendor.')
        return redirect('vendor:accepted_items')
    
    return render(request, 'vendor/decline_reevaluation.html', {'item': item, 'last_offer': last_offer})


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
    
    if tab == 'collector_assigned':
        items = base.filter(status__in=['pickup_scheduled', 'in_transit']).order_by('-created_at')
    elif tab == 'received':
        items = base.filter(status='collected', rejection_count=0).order_by('-created_at')
    elif tab == 'reevaluation':
        items = base.filter(status='collected', rejection_count__gt=0).order_by('-created_at')
    elif tab == 'under_review':
        items = base.filter(status='under_review').order_by('-evaluation_date')
    elif tab == 'completed':
        items = base.filter(status='completed').order_by('-completed_at')
    elif tab == 'returns':
        # Items being returned OR already returned to client
        items = base.filter(status__in=['return_requested', 'return_pickup_scheduled', 'return_in_transit', 'returned_to_client']).order_by('-created_at')
    elif tab == 'transferred':
        # Items that were transferred to another vendor
        items = transferred_items.order_by('-created_at')
    else:
        # ALL tab - show ALL items: current items + transferred items
        tab = 'all'
        current_items = base.exclude(status__in=['pending', 'rejected'])
        # Combine current items with transferred items
        all_item_ids = list(current_items.values_list('pk', flat=True)) + list(transferred_items.values_list('pk', flat=True))
        items = PhotoPost.objects.filter(pk__in=all_item_ids).order_by('-created_at')
    
    # Count for current vendor's items
    current_count = base.exclude(status__in=['pending', 'rejected']).count()
    transferred_count = transferred_items.count()
    
    counts = {
        'all': current_count + transferred_count,  # Include transferred in all count
        'collector_assigned': base.filter(status__in=['pickup_scheduled', 'in_transit']).count(),
        'received': base.filter(status='collected', rejection_count=0).count(),
        'reevaluation': base.filter(status='collected', rejection_count__gt=0).count(),
        'under_review': base.filter(status='under_review').count(),
        'completed': base.filter(status='completed').count(),
        'returns': base.filter(status__in=['return_requested', 'return_pickup_scheduled', 'return_in_transit', 'returned_to_client']).count(),
        'transferred': transferred_count,
    }
    
    # Pass transferred item IDs so template can identify them
    transferred_ids = list(transferred_items.values_list('pk', flat=True))
    
    return render(request, 'vendor/accepted_items.html', {
        'items': items, 
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
    
    # Build vendor-wise history (similar to client view)
    vendor_history = []
    unique_vendors = all_history.values_list('vendor', flat=True).distinct()
    
    vendor_order = 1
    for vendor_id in unique_vendors:
        if vendor_id is None:
            continue
        
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
        
        vendor_history.append({
            'order': vendor_order,
            'vendor': vendor,
            'is_this_vendor': is_this_vendor,
            'is_current': is_vendor_current,
            'evaluations': vendor_evals,
            'total_offers': total_offers,
            'rejected_offers': rejected_offers,
            'accepted_offer': accepted_offer,
            'final_status': final_status,
        })
        vendor_order += 1
    
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
    
    return render(request, 'vendor/item_detail.html', {
        'post': post, 
        'history': my_history,
        'vendor_history': vendor_history,
        'is_current_vendor': is_current_vendor,
        'was_previous_vendor': was_previous_vendor and not is_current_vendor,
        'total_offers': total_offers,
        'rejected_offers': rejected_offers,
        'accepted_offer': accepted_offer,
        'transaction_status': transaction_status,
    })


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