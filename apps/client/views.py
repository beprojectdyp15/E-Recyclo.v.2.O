"""
Client views for E-RECYCLO
Complete client dashboard, upload, and wallet functionality
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse, FileResponse
from decimal import Decimal
import random

from .models import PhotoPost, BulkPickup, CollectionCenter, AppreciationPoints, EvaluationHistory
from .forms import PhotoPostForm, BulkPickupForm
import io
from apps.accounts.models import Account
from apps.ai_services.predictor import predictor
from apps.ai_services.category_mapper import CategoryMapper


# ============================================
# DASHBOARD
# ============================================

@login_required
def dashboard(request):
    """
    Client dashboard with stats and recent activity
    """
    if not request.user.is_client:
        messages.error(request, 'Access denied. This page is for clients only.')
        return redirect('home')
    
    # Get user's statistics
    total_uploads = PhotoPost.objects.filter(user=request.user).count()
    
    pending_uploads = PhotoPost.objects.filter(
        user=request.user,
        status__in=['pending', 'assigned']
    ).count()
    
    completed_uploads = PhotoPost.objects.filter(
        user=request.user,
        status='completed'
    ).count()
    
    # Calculate total earnings from completed uploads
    total_earned = PhotoPost.objects.filter(
        user=request.user,
        status='completed'
    ).aggregate(
        total=Sum('vendor_final_value')
    )['total'] or Decimal('0.00')
    
    # Get wallet balance
    try:
        wallet = request.user.wallet
        wallet_balance = wallet.balance
    except:
        wallet_balance = Decimal('0.00')
    
    # Get appreciation points
    try:
        points_obj = request.user.appreciation_points
        total_points = points_obj.total_points
        current_tier = points_obj.get_current_tier_display()
        # Ensure items_recycled reflects actual completed uploads
        items_recycled = completed_uploads
    except:
        total_points = 0
        current_tier = 'Casual Recycler'
        items_recycled = completed_uploads
    
    # Get recent uploads (last 5)
    recent_uploads = PhotoPost.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Get pending items count
    pending_items = PhotoPost.objects.filter(
        user=request.user,
        status__in=['pending', 'assigned', 'accepted']
    ).count()
    
    context = {
        'page_title': 'Client Dashboard - E-RECYCLO',
        'total_uploads': total_uploads,
        'pending_uploads': pending_uploads,
        'completed_uploads': completed_uploads,
        'total_earned': total_earned,
        'wallet_balance': wallet_balance,
        'total_points': total_points,
        'current_tier': current_tier,
        'items_recycled': items_recycled,
        'recent_uploads': recent_uploads,
        'pending_items': pending_items,
    }
    
    return render(request, 'client/dashboard.html', context)


# ============================================
# UPLOAD E-WASTE
# ============================================

@login_required
def upload_ewaste(request):
    """
    Upload e-waste with photo and details
    Now includes REAL YOLOv8 AI classification
    """
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # AJAX endpoint for AI prediction (when user uploads image)
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if 'photo' in request.FILES:
            try:
                image_file = request.FILES['photo']
                prediction = predictor.predict(image_file)
                
                if prediction.get('success'):
                    # Map the raw YOLO class ID to user-friendly category data
                    class_id = prediction.get('class_id', 5) # Default to 'other' if missing
                    confidence = prediction.get('confidence', 0.0)
                    
                    # Logic: use CategoryMapper to get all metadata (icon, description, display_name)
                    # predictor.predict returns class_id for high-confidence match
                    category_data = CategoryMapper.map_prediction(class_id, confidence)
                    
                    # Merge mapped data into prediction response
                    prediction.update(category_data)
                    
                return JsonResponse(prediction)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'category': 'other',
                    'display_name': 'Other E-Waste',
                    'ai_detected': False,
                }, status=500)
    
    # Normal form submission (with AI category from frontend)
    if request.method == 'POST':
        form = PhotoPostForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Create photo post
                post = form.save(commit=False)
                post.user = request.user
                
                # Get AI category from form (already detected in frontend)
                ai_category = request.POST.get('ai_category', 'other')
                ai_confidence = float(request.POST.get('ai_confidence', 0))
                
                # Map AI category to your existing category system
                category_mapping = {
                    'smartphone': 'smartphone',
                    'laptop': 'laptop',
                    'monitor': 'desktop',  # You might not have monitor, map to desktop
                    'battery': 'battery',
                    'appliance': 'washing_machine',  # Map to closest match
                    'other': 'electronics',
                }
                
                post.ai_category = category_mapping.get(ai_category, 'electronics')
                post.ai_confidence = ai_confidence
                
                # Estimate value based on AI category (your existing logic)
                title_lower = post.title.lower()
                
                if post.ai_category == 'smartphone':
                    post.ai_estimated_value = Decimal(str(random.randint(200, 500)))
                elif post.ai_category == 'laptop':
                    post.ai_estimated_value = Decimal(str(random.randint(500, 1500)))
                elif post.ai_category == 'desktop':
                    post.ai_estimated_value = Decimal(str(random.randint(300, 1000)))
                elif post.ai_category == 'battery':
                    post.ai_estimated_value = Decimal(str(random.randint(50, 200)))
                elif post.ai_category == 'refrigerator':
                    post.ai_estimated_value = Decimal(str(random.randint(800, 2000)))
                elif post.ai_category == 'washing_machine':
                    post.ai_estimated_value = Decimal(str(random.randint(600, 1500)))
                elif post.ai_category == 'ac':
                    post.ai_estimated_value = Decimal(str(random.randint(1000, 3000)))
                else:
                    post.ai_estimated_value = Decimal(str(random.randint(100, 500)))
                
                # Detect condition from title (your existing logic)
                if any(word in title_lower for word in ['new', 'excellent', 'perfect']):
                    post.ai_condition = 'excellent'
                    post.ai_estimated_value = post.ai_estimated_value * Decimal('1.2')
                elif any(word in title_lower for word in ['good', 'working']):
                    post.ai_condition = 'good'
                elif any(word in title_lower for word in ['broken', 'damaged', 'not working']):
                    post.ai_condition = 'poor'
                    post.ai_estimated_value = post.ai_estimated_value * Decimal('0.5')
                else:
                    post.ai_condition = 'fair'
                
                # Adjust value based on quantity
                if post.quantity > 1:
                    post.ai_estimated_value = post.ai_estimated_value * post.quantity
                
                # Set status - stays PENDING until a vendor accepts
                post.status = 'pending'
                
                # Save
                post.save()
                
                # Add appreciation points (your existing logic)
                try:
                    points = request.user.appreciation_points
                    points.add_points(20, f"Uploaded: {post.title}")
                    # Removed items_recycled increment from here - it should only happen on completion
                    points.save()
                except Exception as e:
                    print(f"Could not add points: {e}")
                
                messages.success(
                    request,
                    f'E-waste uploaded successfully! AI detected category: {post.get_ai_category_display()} (₹{post.ai_estimated_value:.2f})'
                )
                return redirect('client:upload_detail', pk=post.pk)
                
            except Exception as e:
                messages.error(request, f'Error uploading e-waste: {str(e)}')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PhotoPostForm()
    
    # Get all categories for manual selection dropdown
    categories = CategoryMapper.get_all_categories()
    
    context = {
        'page_title': 'Upload E-Waste - E-RECYCLO',
        'form': form,
        'categories': categories,
    }
    
    return render(request, 'client/upload_ewaste.html', context)


# ============================================
# MY UPLOADS
# ============================================

@login_required
def my_uploads(request):
    """
    View all user's uploads with filtering
    """
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get filter parameter
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    uploads = PhotoPost.objects.filter(user=request.user)
    
    # Apply filter
    if status_filter:
        uploads = uploads.filter(status=status_filter)
    
    # Order by newest first
    uploads = uploads.order_by('-created_at')
    
    # Get status counts for filter tabs
    status_counts = {
        'all': PhotoPost.objects.filter(user=request.user).count(),
        'pending': PhotoPost.objects.filter(user=request.user, status='pending').count(),
        'assigned': PhotoPost.objects.filter(user=request.user, status='assigned').count(),
        'accepted': PhotoPost.objects.filter(user=request.user, status='accepted').count(),
        'completed': PhotoPost.objects.filter(user=request.user, status='completed').count(),
        'rejected': PhotoPost.objects.filter(user=request.user, status='rejected').count(),
    }
    
    base_qs = PhotoPost.objects.filter(user=request.user)
    tab_counts = {
        '':                 base_qs.count(),
        'pending':          base_qs.filter(status='pending').count(),
        'assigned':         base_qs.filter(status__in=['assigned','accepted']).count(),
        'pickup_scheduled': base_qs.filter(status='pickup_scheduled').count(),
        'in_transit':       base_qs.filter(status='in_transit').count(),
        'under_review':     base_qs.filter(status='under_review').count(),
        'completed':        base_qs.filter(status='completed').count(),
        'rejected':         base_qs.filter(status='rejected').count(),
        'returns':          base_qs.filter(status__in=['return_requested','return_pickup_scheduled','return_in_transit','returned_to_client']).count(),
    }
    
    tab_list = [
        ('All',              '',                 tab_counts['']),
        ('Pending',          'pending',          tab_counts['pending']),
        ('Assigned',         'assigned',         tab_counts['assigned']),
        ('Scheduled',        'pickup_scheduled', tab_counts['pickup_scheduled']),
        ('In Transit',       'in_transit',       tab_counts['in_transit']),
        ('Under Review',     'under_review',     tab_counts['under_review']),
        ('Completed',        'completed',        tab_counts['completed']),
        ('Rejected',         'rejected',         tab_counts['rejected']),
        ('Returns',          'returns',          tab_counts['returns']),
    ]

    if status_filter == 'assigned':
        uploads = base_qs.filter(status__in=['assigned','accepted']).order_by('-created_at')
    elif status_filter == 'returns':
        uploads = base_qs.filter(status__in=['return_requested','return_pickup_scheduled','return_in_transit','returned_to_client']).order_by('-created_at')
    elif status_filter:
        uploads = base_qs.filter(status=status_filter).order_by('-created_at')
    else:
        uploads = base_qs.order_by('-created_at')

    context = {
        'page_title': 'My Uploads - E-RECYCLO',
        'uploads': uploads,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'tab_list': tab_list,
    }
    return render(request, 'client/my_uploads.html', context)


# ============================================
# UPLOAD DETAIL
# ============================================

@login_required
def upload_detail(request, pk):
    """
    View single upload details with full evaluation history
    """
    import math
    from apps.collector.models import CollectorPickup
    
    post = get_object_or_404(PhotoPost, pk=pk, user=request.user)
    
    # Get evaluation history for this post
    history = EvaluationHistory.objects.filter(post=post).order_by('-evaluated_at')
    
    # Get the last offer for vendor_declined_reevaluation case
    last_offer = history.first()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BUILD VENDOR-WISE TRANSACTION HISTORY (Phase-based)
    # ═══════════════════════════════════════════════════════════════════════════
    vendor_history = []
    all_evals = EvaluationHistory.objects.filter(post=post).order_by('evaluated_at')
    current_phase = None
    vendor_order = 1
    
    for eval_entry in all_evals:
        if not current_phase or current_phase['vendor'].id != eval_entry.vendor_id:
            if current_phase:
                # If we are starting a new phase, the previous one is definitely transferred
                current_phase['final_status'] = 'transferred'
                vendor_history.append(current_phase)
                vendor_order += 1
            
            try:
                vendor_obj = Account.objects.get(pk=eval_entry.vendor_id)
            except Account.DoesNotExist:
                continue
                
            current_phase = {
                'order': vendor_order,
                'vendor': vendor_obj,
                'evaluations': [],
                'final_status': 'active'
            }
        
        current_phase['evaluations'].append(eval_entry)

    if current_phase:
        if current_phase['vendor'] == post.vendor:
            if post.status == 'completed': current_phase['final_status'] = 'completed'
            elif post.status == 'returned_to_client': current_phase['final_status'] = 'returned'
            elif post.vendor_declined_reevaluation: current_phase['final_status'] = 'declined_reevaluation'
            else: current_phase['final_status'] = 'active'
        else:
            current_phase['final_status'] = 'transferred'
        vendor_history.append(current_phase)

    # Reverse for Top-to-Bottom (Newest first) logic in UI
    vendor_history.reverse()

    # ═══════════════════════════════════════════════════════════════════════════
    # BUILD COLLECTOR HISTORY
    # ═══════════════════════════════════════════════════════════════════════════
    collector_history = []
    pickups = CollectorPickup.objects.filter(photo_post=post).select_related('collector').order_by('created_at')
    
    # We need vendors in chronological order to determine transfer addresses
    unique_vids = []
    for vid in EvaluationHistory.objects.filter(post=post).order_by('evaluated_at').values_list('vendor_id', flat=True):
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

    # Process chronologically to assign Order 1, 2, 3...
    for i, p in enumerate(pickups, 1):
        c_type = "Primary Pickup"
        pickup_name = "Pickup From Client"
        pickup_addr = post.address
        pickup_coords = {'lat': post.latitude, 'long': post.longitude}
        delivery_name = "Deliver To Vendor"
        delivery_addr = "N/A"
        delivery_coords = {'lat': 0, 'long': 0}
        
        # Determine Addresses based on type
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
            # Primary Pickup
            target_v = None
            if vendor_objs:
                target_v = vendor_objs[0]
            elif post.vendor:
                target_v = post.vendor
                
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
    # Reverse for UI (Newest at top)
    collector_history.reverse()

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE SITUATIONAL DESCRIPTION (CTC)
    # ═══════════════════════════════════════════════════════════════════════════
    status_msg = "Your request is being processed."
    s = post.status
    is_transfer = len(vendor_history) > 0
    if s == 'pending': status_msg = "Your item is currently visible to nearby recyclers. We'll notify you as soon as someone accepts the request."
    elif s == 'assigned': status_msg = "Good news! A certified recycler has been assigned. They are now arranging a collector for pickup."
    elif s == 'accepted': status_msg = "Assignment confirmed. A logistics partner is being matched to your location for the pickup."
    elif s == 'pickup_scheduled':
        if post.collector:
            if is_transfer:
                status_msg = "Transfer scheduled. The assigned collector will arrive at the previous recycler's facility soon to pick up your item."
            else:
                status_msg = "Pickup is scheduled. The assigned collector will arrive at your address soon."
        else:
            if is_transfer:
                status_msg = "Good news! A new certified recycler has been assigned. We are now looking for a nearby collector to transfer your item."
            else:
                status_msg = "Good news! A certified recycler has been assigned. We are now looking for a nearby collector to schedule your pickup."
    elif s == 'in_transit':
        if is_transfer:
            status_msg = "Your item is safely in transit and heading to the new recycling facility for technical inspection."
        else:
            status_msg = "Your item is safely in transit and heading to the recycling facility for physical verification."
    elif s == 'collected':
        if post.vendor_declined_reevaluation:
            status_msg = "The recycler has declined your re-evaluation request. You may now accept their last offer, transfer to another vendor, or request item return."
        elif post.rejection_count and post.rejection_count > 0:
            status_msg = "Re-evaluation requested! The recycler is reviewing your expected price and notes to provide a revised offer."
        else:
            status_msg = "Item delivered! The recycler is performing a deep technical inspection to provide you with the most accurate offer."
    elif s == 'under_review':
        if post.offer_count and post.offer_count > 1:
            status_msg = f"The recycler's re-evaluation (Offer #{post.offer_count}) is ready! Please review the revised evaluation details below and select your preferred action."
        else:
            status_msg = "The recycler's evaluation is ready! Please review the evaluation details below and select your preferred action."
    elif s == 'return_requested': status_msg = "Return process initiated. We are searching for a collector to return the item to your registered address."
    elif s == 'return_pickup_scheduled': status_msg = "A collector is en-route to the recycling facility to pick up your item for return."
    elif s == 'return_in_transit': status_msg = "The collector has picked up your item and is on their way to deliver it back to you."
    elif s == 'returned_to_client': status_msg = "Your item has been successfully returned to your registered address."
    elif s == 'completed': status_msg = "Process complete! Thank you for contributing to a greener planet. Your recycling certificate and wallet credit are now active."
    elif s == 'rejected': status_msg = "The request was unfortunately rejected. You can check the logs for details or try uploading a different item."

    # Prepare current status strings for top badges
    vendor_status_tag = post.get_status_display()
    if s == 'under_review': vendor_status_tag = "Evaluation Ready"
    elif s == 'collected':
        if post.vendor_declined_reevaluation:
            vendor_status_tag = "Re-evaluation Declined"
        elif post.rejection_count and post.rejection_count > 0:
            vendor_status_tag = "Re-evaluating"
        else:
            vendor_status_tag = "Inspecting"
    elif s == 'pickup_scheduled' and not post.collector: vendor_status_tag = "Searching for Collector"

    client_status_tag = post.get_status_display().upper()
    if s == 'under_review': client_status_tag = "EVALUATION READY"
    elif s == 'collected':
        if post.vendor_declined_reevaluation:
            client_status_tag = "RE-EVALUATION DECLINED"
        elif post.rejection_count and post.rejection_count > 0:
            client_status_tag = "RE-EVALUATING"
        else:
            client_status_tag = "INSPECTING"
    elif s == 'pickup_scheduled' and not post.collector:
        client_status_tag = "SEARCHING FOR COLLECTOR"

    collector_status_tag = "Pending"
    if s in ['collected', 'under_review', 'completed']: 
        collector_status_tag = "Delivered to Vendor"
    elif s in ['assigned', 'accepted', 'pickup_scheduled', 'return_pickup_scheduled']: 
        if (s == 'pickup_scheduled' or s == 'return_pickup_scheduled') and not post.collector and not post.return_collector:
            collector_status_tag = "Searching"
        else:
            collector_status_tag = "Scheduled"
    elif s in ['in_transit', 'return_in_transit']: 
        collector_status_tag = "In Transit"
    elif s == 'returned_to_client': 
        collector_status_tag = "Returned to you"

    # Count TRANSFERS strictly by counting how many UNIQUE vendors have evaluated this item
    v_ids_hist = list(EvaluationHistory.objects.filter(post=post).values_list('vendor_id', flat=True))
    unique_past_vendors = set([vid for vid in v_ids_hist if vid is not None])
    transfer_count = max(0, len(unique_past_vendors) - 1)
    can_transfer = transfer_count < 2

    # Check if there are other vendors within 5km for transfer availability
    nearby_vendors_exist = False
    if post.vendor_declined_reevaluation and can_transfer:
        def calc_dist(lat1, lon1, lat2, lon2):
            R = 6371
            lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
            delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
            a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad)*math.cos(lat2_rad)*math.sin(delta_lon/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        excluded_vendor_ids = list(unique_past_vendors)
        vendors = Account.objects.filter(
            is_vendor=True, is_active=True,
            profile_completion__approval_status='approved'
        ).exclude(pk__in=excluded_vendor_ids)
        
        for vendor in vendors:
            try:
                vp = vendor.vendor_profile
                if vp.latitude and vp.longitude:
                    if calc_dist(post.latitude, post.longitude, vp.latitude, vp.longitude) <= 5:
                        nearby_vendors_exist = True
                        break
            except: continue

    context = {
        'page_title': f'Upload: {post.title} - E-RECYCLO',
        'post': post,
        'history': history,
        'vendor_history': vendor_history,
        'collector_history': collector_history,
        'vendor_status_tag': vendor_status_tag,
        'client_status_tag': client_status_tag,
        'collector_status_tag': collector_status_tag,
        'status_msg': status_msg,
        'last_offer': history.first(),
        'transfer_count': transfer_count,
        'can_transfer': can_transfer,
        'nearby_vendors_exist': nearby_vendors_exist,
        'is_transfer': is_transfer,
    }
    
    return render(request, 'client/upload_detail.html', context)


# ============================================
# WALLET
# ============================================

@login_required
def wallet(request):
    """
    View wallet balance and transaction history
    """
    from django.core.paginator import Paginator
    
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get wallet
    try:
        wallet = request.user.wallet
        # Get all transactions ordered by recent first
        transactions_list = wallet.transactions.all().order_by('-created_at')
        
        # Implement Pagination: 5 transactions per page
        paginator = Paginator(transactions_list, 5)
        page_number = request.GET.get('page')
        transactions = paginator.get_page(page_number)
    except:
        wallet = None
        transactions = []
    
    # Calculate statistics
    total_earned = PhotoPost.objects.filter(
        user=request.user,
        status='completed'
    ).aggregate(total=Sum('vendor_final_value'))['total'] or Decimal('0.00')
    
    context = {
        'page_title': 'My Wallet - E-RECYCLO',
        'wallet': wallet,
        'transactions': transactions,
        'total_earned': total_earned,
    }
    
    return render(request, 'client/wallet.html', context)


# ============================================
# COLLECTION CENTERS
# ============================================

@login_required
def collection_centers(request):
    """
    Find nearby collection centers for drop-off
    """
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all active collection centers
    centers = CollectionCenter.objects.filter(is_active=True)
    
    # If user provides location, calculate distances
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    
    if user_lat and user_lng:
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
            
            # Calculate distance for each center
            centers_with_distance = []
            for center in centers:
                distance = center.distance_from(user_lat, user_lng)
                centers_with_distance.append({
                    'center': center,
                    'distance': distance
                })
            
            # Sort by distance (nearest first)
            centers_with_distance.sort(key=lambda x: x['distance'])
            centers = centers_with_distance
        except (ValueError, TypeError):
            pass
    
    context = {
        'page_title': 'Collection Centers - E-RECYCLO',
        'centers': centers,
    }
    
    return render(request, 'client/collection_centers.html', context)


# ============================================
# BULK PICKUP
# ============================================

@login_required
def bulk_pickup(request):
    """
    View bulk pickup status for low-value items
    """
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get or create active bulk pickup
    bulk_pickup_obj = BulkPickup.objects.filter(
        user=request.user,
        status__in=['collecting', 'ready']
    ).first()
    
    if not bulk_pickup_obj:
        # Create new bulk pickup
        try:
            profile = request.user.client_profile
            address = profile.address or ''
        except:
            address = ''
        
        bulk_pickup_obj = BulkPickup.objects.create(
            user=request.user,
            address=address,
            latitude=0.0,
            longitude=0.0,
        )
    
    # Update item count
    bulk_pickup_obj.update_item_count()
    
    # Get items in bulk pickup
    bulk_items = bulk_pickup_obj.items.all()
    
    context = {
        'page_title': 'Bulk Pickup - E-RECYCLO',
        'bulk_pickup': bulk_pickup_obj,
        'bulk_items': bulk_items,
    }
    
    return render(request, 'client/bulk_pickup.html', context)



@login_required
def review_offer(request, pk):
    """Client reviews offer. Saves history on reject, optionally adds rejection reason."""
    post = get_object_or_404(PhotoPost, pk=pk, user=request.user, status='under_review')
    history = EvaluationHistory.objects.filter(post=post).order_by('-evaluated_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'accept':
            post.status = 'completed'
            post.completed_at = timezone.now()
            post.save()
            # Mark history entry as accepted
            current = history.first()
            if current:
                current.rejected_by_client = False
                current.client_accepted = True
                current.client_choice = 'accepted'
                current.save()
            # Credit wallet
            wallet_credited = False
            if post.vendor_final_value and post.vendor_final_value > 0:
                try:
                    post.user.wallet.credit(post.vendor_final_value, f"Offer accepted: {post.title}")
                    wallet_credited = True
                except Exception:
                    pass
            # Award eco-points
            points_awarded = 0
            try:
                pts, _ = AppreciationPoints.objects.get_or_create(user=request.user)
                points_awarded = (post.eco_points_awarded or 0) + 20
                pts.add_points(points_awarded, f"Recycling completed: {post.title}")
                pts.items_recycled += 1  # Increment on actual completion
                pts.save()
            except Exception:
                pass
            
            # Show success message and redirect to upload_detail (user can download certificate from there)
            msg = f'🎉 Offer accepted! '
            if post.vendor_final_value:
                msg += f'₹{post.vendor_final_value} credited to your wallet. '
            msg += f'+{points_awarded} eco-points earned. You can now download your certificate.'
            messages.success(request, msg)
            return redirect('client:upload_detail', pk=pk)

        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', '').strip()
            client_requested_value = request.POST.get('expected_price')
            
            # Mark current history entry rejected
            current = history.first()
            if current:
                current.rejected_by_client = True
                current.rejection_reason = rejection_reason
                
                # Save requested value if provided
                if client_requested_value:
                    try:
                        current.client_requested_value = Decimal(client_requested_value)
                    except:
                        pass
                        
                current.client_choice = 'rejected'
                current.save()
            # Reset item to collected for re-evaluation
            post.status = 'collected'
            post.rejection_count = (post.rejection_count or 0) + 1
            post.vendor_final_value = None
            post.evaluation_type = ''; post.eco_points_awarded = 0
            post.vendor_remarks = ''; post.condition_notes = ''; post.price_breakdown = ''
            post.evaluation_date = None
            post.save()
            messages.info(request, f'Offer rejected. Vendor notified to re-evaluate (rejection #{post.rejection_count}).')
            return redirect('client:upload_detail', pk=pk)

    proposed_action = request.GET.get('action', 'reject')
    return render(request, 'client/review_offer.html', {'post': post, 'history': history, 'proposed_action': proposed_action})


@login_required
def request_return(request, pk):
    """Client requests item returned from vendor.
    Only allowed when:
    - Vendor has sent an offer (status = 'under_review')
    - Vendor has declined re-evaluation (vendor_declined_reevaluation = True)
    NOT allowed during 'collected' status while waiting for first evaluation.
    """
    post = get_object_or_404(PhotoPost, pk=pk, user=request.user)
    history = EvaluationHistory.objects.filter(post=post)
    
    # Return is only allowed when:
    # 1. Status is 'under_review' (vendor sent an offer, client can choose return instead)
    # 2. vendor_declined_reevaluation is True (vendor refused to re-evaluate)
    can_request_return = (
        post.status == 'under_review' or 
        (post.status == 'collected' and post.vendor_declined_reevaluation)
    )
    
    if not can_request_return:
        messages.error(request, 'Return can only be requested after vendor sends an offer or declines re-evaluation.')
        return redirect('client:upload_detail', pk=pk)
    
    if request.method == 'POST':
        # DON'T generate return OTPs here - they will be generated when return_collector accepts
        # The model's save() method handles this when return_collector_id is set
        
        # Set status to return_requested - collectors will see and claim it
        post.status = 'return_requested'
        post.vendor_declined_reevaluation = False  # Clear this flag
        post.save()
        
        # Log this decision in history
        last_eval = history.first()
        if last_eval:
            last_eval.client_choice = 'return'
            last_eval.save()
        
        messages.success(request, 'Return requested! Nearby collectors will be notified and can claim this pickup.')
        return redirect('client:upload_detail', pk=pk)
    
    return render(request, 'client/request_return.html', {'post': post, 'history': history})


from django.views.decorators.clickjacking import xframe_options_exempt

@login_required
@xframe_options_exempt
def download_certificate(request, pk):
    """Generate and stream a professional PDF recycling certificate."""
    post = get_object_or_404(PhotoPost, pk=pk, user=request.user, status='completed')
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from django.http import FileResponse

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2*cm, bottomMargin=2*cm)
        GREEN = colors.HexColor('#16a34a'); LIGHT_GRN = colors.HexColor('#f0fdf4')
        DARK = colors.HexColor('#1e293b'); GRAY = colors.HexColor('#64748b')

        def h(tag, txt, **kw): return Paragraph(txt, ParagraphStyle(tag, **kw))
        story = []
        story.append(h('brand', '<font color="#16a34a"><b>E-RECYCLO</b></font>', fontSize=32, alignment=TA_CENTER, spaceAfter=2))
        story.append(h('tag', 'Electronic Waste Recycling Platform · Maharashtra, India', fontSize=10, alignment=TA_CENTER, textColor=GRAY, spaceAfter=8))
        story.append(HRFlowable(width='100%', thickness=3, color=GREEN, spaceAfter=14))
        story.append(h('cert', 'CERTIFICATE OF RECYCLING CONTRIBUTION', fontSize=17, alignment=TA_CENTER, textColor=GREEN, fontName='Helvetica-Bold', spaceAfter=6))
        story.append(h('sub', 'This certifies that the following electronic item has been responsibly processed.', fontSize=10, alignment=TA_CENTER, textColor=GRAY, spaceAfter=14))
        story.append(h('nm', f'Awarded to: <b>{post.user.get_full_name()}</b>', fontSize=14, alignment=TA_CENTER, spaceAfter=3))
        cd = post.completed_at.strftime('%d %B %Y') if post.completed_at else timezone.now().strftime('%d %B %Y')
        story.append(h('dt', f'Date of Completion: {cd}', fontSize=10, alignment=TA_CENTER, textColor=GRAY, spaceAfter=16))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.lightgrey, spaceAfter=12))

        story.append(h('s1', 'ITEM DETAILS', fontSize=11, fontName='Helvetica-Bold', textColor=GREEN, spaceAfter=7))
        irows = [
            [Paragraph('<b>Field</b>', ParagraphStyle('th', fontSize=9, textColor=colors.white)),
             Paragraph('<b>Details</b>', ParagraphStyle('th2', fontSize=9, textColor=colors.white))],
            ['Item Name', post.title],
            ['Category', post.get_ai_category_display()],
            ['Condition (AI)', post.get_ai_condition_display() or 'N/A'],
            ['Quantity', str(post.quantity)],
            ['Evaluation', {'repair':'Repairable','recycle':'Recyclable','ecopoints':'Eco-Points Only'}.get(post.evaluation_type,'N/A')],
            ['Total Offers Made', str(post.offer_count or 1)],
            ['Vendor', post.vendor.get_full_name() if post.vendor else 'N/A'],
            ['Collector', post.collector.get_full_name() if post.collector else 'N/A'],
            ['Address', post.address[:70] + '…' if len(post.address) > 70 else post.address],
        ]
        ts = [('BACKGROUND',(0,0),(-1,0),GREEN),('TEXTCOLOR',(0,0),(-1,0),colors.white),
              ('FONTNAME',(0,1),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),
              ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT_GRN]),
              ('GRID',(0,0),(-1,-1),0.5,colors.lightgrey),('PADDING',(0,0),(-1,-1),6)]
        t = Table(irows, colWidths=[4.5*cm, 12.5*cm]); t.setStyle(TableStyle(ts)); story.append(t)
        story.append(Spacer(1, 0.5*cm))

        story.append(HRFlowable(width='100%', thickness=1, color=colors.lightgrey, spaceAfter=10))
        story.append(h('s2', 'FINANCIAL SUMMARY', fontSize=11, fontName='Helvetica-Bold', textColor=GREEN, spaceAfter=7))
        frows = [
            [Paragraph('<b>Field</b>', ParagraphStyle('fh', fontSize=9, textColor=colors.white)),
             Paragraph('<b>Value</b>', ParagraphStyle('fh2', fontSize=9, textColor=colors.white))],
            ['AI Estimated Value', f'Rs. {post.ai_estimated_value or 0}'],
            ['Final Offered Amount', f'Rs. {post.vendor_final_value or 0}'],
            ['Eco-Points Awarded', f'{post.eco_points_awarded or 0} + 20 bonus = {(post.eco_points_awarded or 0)+20} pts'],
            ['Wallet Credited', f'Rs. {post.vendor_final_value or 0}'],
        ]
        ft = Table(frows, colWidths=[5*cm, 12*cm]); ft.setStyle(TableStyle(ts)); story.append(ft)
        story.append(Spacer(1, 0.4*cm))

        if post.price_breakdown:
            story.append(HRFlowable(width='100%', thickness=1, color=colors.lightgrey, spaceAfter=10))
            story.append(h('s3', 'VENDOR PRICE BREAKDOWN', fontSize=11, fontName='Helvetica-Bold', textColor=GREEN, spaceAfter=6))
            story.append(h('pb', post.price_breakdown.replace('\n','<br/>'), fontSize=9, textColor=DARK, leading=14, backColor=LIGHT_GRN, borderPad=8, spaceAfter=10))

        if post.vendor_remarks:
            story.append(h('s4', 'VENDOR ASSESSMENT', fontSize=11, fontName='Helvetica-Bold', textColor=GREEN, spaceAfter=6))
            story.append(h('vr', post.vendor_remarks.replace('\n','<br/>'), fontSize=9, textColor=DARK, leading=14, backColor=LIGHT_GRN, borderPad=8, spaceAfter=10))

        story.append(HRFlowable(width='100%', thickness=1, color=colors.lightgrey, spaceAfter=10))
        story.append(h('s5', 'ENVIRONMENTAL IMPACT', fontSize=11, fontName='Helvetica-Bold', textColor=GREEN, spaceAfter=6))
        story.append(h('ei',
            'By responsibly recycling your e-waste through E-RECYCLO, you have:<br/>'
            '• Prevented toxic materials from entering landfills<br/>'
            '• Enabled recovery of valuable raw materials<br/>'
            '• Reduced carbon footprint from manufacturing new devices<br/>'
            '• Supported the circular economy in Maharashtra',
            fontSize=9, textColor=DARK, leading=15, spaceAfter=12))

        story.append(HRFlowable(width='100%', thickness=2, color=GREEN, spaceAfter=8))
        story.append(h('cid', f'Certificate ID: EREC-{post.pk:06d}-{(post.completed_at or timezone.now()).year}  |  Verified by E-RECYCLO Platform', fontSize=8, alignment=TA_CENTER, textColor=GRAY))
        story.append(h('ft', 'E-RECYCLO · Responsible E-Waste Management · Maharashtra, India', fontSize=8, alignment=TA_CENTER, textColor=GRAY))

        doc.build(story); buf.seek(0)
        inline = request.GET.get('inline') == 'true'
        return FileResponse(buf, as_attachment=not inline, filename=f'erecyclo_certificate_{post.pk}.pdf')

    except Exception as e:
        messages.error(request, f'Could not generate certificate: {str(e)}')
        return redirect('client:upload_detail', pk=pk)


@login_required
def download_statement(request):
    """Generate and stream a professional PDF bank-grade wallet statement."""
    from apps.payments.models import Transaction
    from datetime import timedelta
    
    period = request.GET.get('period', 'all')
    try:
        user_wallet = request.user.wallet
    except:
        messages.error(request, 'Wallet not found.')
        return redirect('client:wallet')
        
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
            except Exception as e:
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
        story.append(Paragraph('Responsible E-Waste Management & Digital Wallet', get_style('tag', fontSize=9, textColor=GRAY)))
        story.append(Spacer(1, 0.2*cm))
        story.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=10))
        
        # --- STATEMENT HEADER ---
        story.append(Paragraph('WALLET TRANSACTION STATEMENT', get_style('title', fontSize=16, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=10)))
        
        # --- CUSTOMER & ACCOUNT INFO ---
        info_data = [
            [Paragraph(f'<b>Customer Name:</b> {request.user.get_full_name() or request.user.email}', get_style('info')), 
             Paragraph(f'<b>Statement Period:</b> {date_display}', get_style('info'))],
            [Paragraph(f'<b>User ID:</b> #{request.user.pk}', get_style('info')), 
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
            row = [
                txn.created_at.strftime('%d/%m/%y'),
                Paragraph(txn.description[:50], get_style('td', fontSize=9)),
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
        story.append(Paragraph('E-RECYCLO Platform | Maharashtra, India | support@erecyclo.com', 
                             get_style('ft', fontSize=8, alignment=TA_CENTER, textColor=GRAY)))

        doc.build(story); buf.seek(0)
        return FileResponse(buf, as_attachment=True, filename=f'erecyclo_statement_{period}_{now.strftime("%Y%m%d")}.pdf')

    except Exception as e:
        messages.error(request, f'Could not generate statement: {str(e)}')
        return redirect('client:wallet')

# ============================================
# ACCEPT LAST OFFER (when vendor declines re-eval)
# ============================================

@login_required
def accept_last_offer(request, pk):
    """Accept the last offer when vendor declined re-evaluation."""
    post = get_object_or_404(PhotoPost, pk=pk, user=request.user)
    
    if not post.vendor_declined_reevaluation:
        messages.error(request, 'This action is not available.')
        return redirect('client:upload_detail', pk=pk)
    
    history = EvaluationHistory.objects.filter(post=post).order_by('-evaluated_at')
    last_offer = history.first()
    
    if not last_offer:
        messages.error(request, 'No previous offer found.')
        return redirect('client:upload_detail', pk=pk)
    
    if request.method == 'POST':
        # Mark offer as accepted
        last_offer.client_accepted = True
        last_offer.rejected_by_client = False
        last_offer.client_choice = 'accepted'
        last_offer.save()
        
        # Restore the last offer values to the post
        post.vendor_final_value = last_offer.vendor_final_value
        post.eco_points_awarded = last_offer.eco_points_awarded
        post.evaluation_type = last_offer.evaluation_type
        post.vendor_remarks = last_offer.vendor_remarks
        post.condition_notes = last_offer.condition_notes
        post.price_breakdown = last_offer.price_breakdown
        post.status = 'completed'
        post.completed_at = timezone.now()
        post.vendor_declined_reevaluation = False
        post.save()
        
        # Credit wallet
        wallet_credited = False
        if post.vendor_final_value and post.vendor_final_value > 0:
            try:
                post.user.wallet.credit(post.vendor_final_value, f"Offer accepted: {post.title}")
                wallet_credited = True
            except Exception:
                pass
        
        # Award eco-points
        points_awarded = 0
        try:
            pts, _ = AppreciationPoints.objects.get_or_create(user=request.user)
            points_awarded = (post.eco_points_awarded or 0) + 20
            pts.add_points(points_awarded, f"Recycling completed: {post.title}")
        except Exception:
            pass
        
        # Show success message and redirect to upload_detail (which shows completed status)
        msg = f'🎉 Offer accepted! ₹{post.vendor_final_value} credited to wallet. +{points_awarded} eco-points earned.'
        messages.success(request, msg)
        return redirect('client:upload_detail', pk=pk)
    
    return render(request, 'client/accept_last_offer.html', {'post': post, 'last_offer': last_offer})


# ============================================
# TRANSFER TO ANOTHER VENDOR
# ============================================

@login_required
def transfer_to_vendor(request, pk):
    """Transfer item to another nearby vendor - item becomes visible to nearby vendors.
    Max 2 transfers allowed per item.
    """
    import math
    
    post = get_object_or_404(PhotoPost, pk=pk, user=request.user)
    
    if not post.vendor_declined_reevaluation:
        messages.error(request, 'This action is not available.')
        return redirect('client:upload_detail', pk=pk)
    
    # Count TRANSFERS strictly by counting how many UNIQUE vendors have evaluated this item
    # Original Vendor (1) -> 0 transfers
    # Second Vendor (2) -> 1 successful transfer performed
    # Third Vendor (3) -> 2 successful transfers performed (Limit reached if user tries to transfer again)
    v_ids = list(EvaluationHistory.objects.filter(post=post).values_list('vendor_id', flat=True))
    unique_vendors = set([vid for vid in v_ids if vid is not None])
    transfer_count = max(0, len(unique_vendors) - 1)
    
    # Cache the list for the next section (excluded vendors)
    previous_vendors = list(unique_vendors)
    
    # Max 2 transfers allowed
    if transfer_count >= 2:
        messages.error(request, f'Maximum 2 vendor transfers allowed per item (currently at {transfer_count}). You can request a return instead.')
        return redirect('client:upload_detail', pk=pk)
    
    def calc_dist(lat1, lon1, lat2, lon2):
        R = 6371
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad)*math.cos(lat2_rad)*math.sin(delta_lon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # Get list of vendors who already had this item (to exclude them)
    excluded_vendor_ids = list(previous_vendors)
    if post.vendor and post.vendor.pk not in excluded_vendor_ids:
        excluded_vendor_ids.append(post.vendor.pk)
    
    # Check if there are other vendors within 5km (excluding previous vendors)
    nearby_vendors_count = 0
    nearby_vendor_names = []
    vendors = Account.objects.filter(
        is_vendor=True, is_active=True,
        profile_completion__approval_status='approved'
    ).exclude(pk__in=excluded_vendor_ids)
    
    for vendor in vendors:
        try:
            vp = vendor.vendor_profile
            if vp.latitude and vp.longitude:
                if calc_dist(post.latitude, post.longitude, vp.latitude, vp.longitude) <= 5:
                    nearby_vendors_count += 1
                    nearby_vendor_names.append(vendor.get_full_name())
        except:
            continue
    
    if request.method == 'POST':
        if nearby_vendors_count == 0:
            messages.error(request, 'No other vendor available within 5km. You can request a return instead.')
            return redirect('client:upload_detail', pk=pk)
        
        # Reset post - make it visible to OTHER nearby vendors (like pending)
        post.vendor = None  # Clear vendor so other vendors can see and accept
        post.status = 'pending'  # Back to pending - nearby vendors will see it
        post.vendor_declined_reevaluation = False
        post.vendor_final_value = None
        post.evaluation_type = ''
        post.eco_points_awarded = 0
        post.vendor_remarks = ''
        post.condition_notes = ''
        post.price_breakdown = ''
        post.evaluation_date = None
        # Reset for fresh start with new vendor
        post.rejection_count = 0
        post.offer_count = 0  # Reset offer count
        post.collector = None
        post.pickup_otp = ''
        post.delivery_otp = ''
        post.save()

        # Log transfer in history
        last_eval = EvaluationHistory.objects.filter(post=post).order_by('-evaluated_at').first()
        if last_eval:
            last_eval.client_choice = 'transfer'
            last_eval.save()
        
        messages.success(request, f'Item is now visible to {nearby_vendors_count} nearby vendor(s). The first one to accept will receive it.')
        return redirect('client:upload_detail', pk=pk)
    
    return render(request, 'client/transfer_to_vendor.html', {
        'post': post,
        'nearby_vendors_count': nearby_vendors_count,
        'transfer_count': transfer_count,
        'transfers_remaining': 2 - transfer_count,
    })