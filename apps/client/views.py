"""
Client views for E-RECYCLO
Complete client dashboard, upload, and wallet functionality
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
import random

from .models import PhotoPost, BulkPickup, CollectionCenter, AppreciationPoints, EvaluationHistory
from .forms import PhotoPostForm, BulkPickupForm
import io
from apps.accounts.models import Account
from apps.ai_services.predictor import EWastePredictor
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
        items_recycled = points_obj.items_recycled
    except:
        total_points = 0
        current_tier = 'Casual Recycler'
        items_recycled = 0
    
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
                prediction = EWastePredictor.predict(image_file)
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
                    points.items_recycled += 1
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
        '':             base_qs.count(),
        'pending':      base_qs.filter(status='pending').count(),
        'in_progress':  base_qs.filter(status__in=['assigned','accepted','pickup_scheduled','in_transit','collected']).count(),
        'under_review': base_qs.filter(status='under_review').count(),
        'completed':    base_qs.filter(status='completed').count(),
        'rejected':     base_qs.filter(status='rejected').count(),
        'returns':      base_qs.filter(status__in=['return_requested','return_pickup_scheduled','return_in_transit','returned_to_client']).count(),
    }
    tab_list = [
        ('All',          '',             tab_counts['']),
        ('Pending',      'pending',      tab_counts['pending']),
        ('In Progress',  'in_progress',  tab_counts['in_progress']),
        ('Offer Review', 'under_review', tab_counts['under_review']),
        ('Completed',    'completed',    tab_counts['completed']),
        ('Rejected',     'rejected',     tab_counts['rejected']),
        ('Returns',      'returns',      tab_counts['returns']),
    ]
    if status_filter == 'in_progress':
        uploads = base_qs.filter(status__in=['assigned','accepted','pickup_scheduled','in_transit','collected']).order_by('-created_at')
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
    # BUILD VENDOR-WISE TRANSACTION HISTORY
    # Each vendor gets their own card with all their evaluations and collector info
    # ═══════════════════════════════════════════════════════════════════════════
    vendor_history = []
    unique_vendors = history.values_list('vendor', flat=True).distinct()
    
    # Get all collector pickups for this post
    all_pickups = CollectorPickup.objects.filter(photo_post=post).select_related('collector').order_by('created_at')
    
    vendor_order = 1
    for vendor_id in unique_vendors:
        if vendor_id is None:
            continue
        
        try:
            vendor = Account.objects.get(pk=vendor_id)
        except Account.DoesNotExist:
            continue
        
        # Get all evaluations by this vendor
        vendor_evals = history.filter(vendor_id=vendor_id).order_by('evaluated_at')
        
        # Determine if this vendor is current, previous, or transferred
        is_current = post.vendor and post.vendor.pk == vendor_id
        
        # Find collector who delivered to this vendor
        # For transfers, look for pickup with TRANSFER_FROM_VENDOR marker
        delivery_collector = None
        pickup_collector = None
        
        for pickup in all_pickups:
            if pickup.status == 'completed':
                # This collector completed a delivery
                if delivery_collector is None:
                    delivery_collector = pickup.collector
        
        # Calculate totals for this vendor
        total_offers = vendor_evals.count()
        accepted_offer = vendor_evals.filter(rejected_by_client=False).last()
        rejected_offers = vendor_evals.filter(rejected_by_client=True).count()
        
        # Determine final status with this vendor
        if is_current:
            if post.status == 'completed':
                final_status = 'completed'
            elif post.status == 'returned_to_client':
                final_status = 'returned'
            elif post.vendor_declined_reevaluation:
                final_status = 'declined_reevaluation'
            else:
                final_status = 'active'
        else:
            # Previous vendor - check if transferred
            final_status = 'transferred'
        
        vendor_history.append({
            'order': vendor_order,
            'vendor': vendor,
            'is_current': is_current,
            'evaluations': vendor_evals,
            'total_offers': total_offers,
            'rejected_offers': rejected_offers,
            'accepted_offer': accepted_offer,
            'final_status': final_status,
            'delivery_collector': delivery_collector,
        })
        vendor_order += 1
    
    # Reverse to show oldest vendor first (Vendor 1, Vendor 2, Vendor 3)
    vendor_history = sorted(vendor_history, key=lambda x: x['order'])
    
    # Count TRANSFERS (not vendors) - first vendor is not a transfer
    previous_vendors = list(history.values_list('vendor_id', flat=True).distinct())
    previous_vendors = [v for v in previous_vendors if v is not None]
    transfer_count = max(0, len(previous_vendors) - 1)
    can_transfer = transfer_count < 2  # Max 2 transfers allowed
    
    # Check if there are other vendors within 5km
    nearby_vendors_exist = False
    if post.vendor_declined_reevaluation and can_transfer:
        def calc_dist(lat1, lon1, lat2, lon2):
            R = 6371
            lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
            delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
            a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad)*math.cos(lat2_rad)*math.sin(delta_lon/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        excluded_vendor_ids = list(previous_vendors)
        if post.vendor and post.vendor.pk not in excluded_vendor_ids:
            excluded_vendor_ids.append(post.vendor.pk)
        
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
            except:
                continue
    
    # Get all collectors who worked on this item
    collectors_history = []
    if post.collector:
        collectors_history.append({'collector': post.collector, 'type': 'Current Pickup'})
    if post.return_collector:
        collectors_history.append({'collector': post.return_collector, 'type': 'Return'})
    
    # Check if this is a vendor transfer
    is_vendor_transfer = post.vendor_remarks and post.vendor_remarks.startswith('TRANSFER_FROM_VENDOR:')
    
    context = {
        'page_title': f'Upload: {post.title} - E-RECYCLO',
        'post': post,
        'history': history,
        'vendor_history': vendor_history,  # NEW: Vendor-wise history cards
        'last_offer': last_offer,
        'transfer_count': transfer_count,
        'can_transfer': can_transfer,
        'nearby_vendors_exist': nearby_vendors_exist,
        'collectors_history': collectors_history,
        'is_vendor_transfer': is_vendor_transfer,
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
    if not request.user.is_client:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get wallet
    try:
        wallet = request.user.wallet
        transactions = wallet.transactions.all().order_by('-created_at')[:50]
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
            # Mark current history entry rejected
            current = history.first()
            if current:
                current.rejected_by_client = True
                current.rejection_reason = rejection_reason
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

    return render(request, 'client/review_offer.html', {'post': post, 'history': history})


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
        
        messages.success(request, 'Return requested! Nearby collectors will be notified and can claim this pickup.')
        return redirect('client:upload_detail', pk=pk)
    
    return render(request, 'client/request_return.html', {'post': post, 'history': history})


@login_required
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
        return FileResponse(buf, as_attachment=True, filename=f'erecyclo_certificate_{post.pk}.pdf')

    except ImportError:
        messages.error(request, 'PDF library missing. Run: pip install reportlab')
        return redirect('client:upload_detail', pk=pk)

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
    
    # Count TRANSFERS (not vendors) - first vendor is not a transfer
    # Transfer count = unique vendors - 1
    previous_vendors = list(EvaluationHistory.objects.filter(post=post).values_list('vendor_id', flat=True).distinct())
    previous_vendors = [v for v in previous_vendors if v is not None]
    transfer_count = max(0, len(previous_vendors) - 1)
    
    # Max 2 transfers allowed
    if transfer_count >= 2:
        messages.error(request, 'Maximum 2 vendor transfers allowed per item. You can request a return instead.')
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
        
        messages.success(request, f'Item is now visible to {nearby_vendors_count} nearby vendor(s). The first one to accept will receive it.')
        return redirect('client:upload_detail', pk=pk)
    
    return render(request, 'client/transfer_to_vendor.html', {
        'post': post,
        'nearby_vendors_count': nearby_vendors_count,
        'transfer_count': transfer_count,
        'transfers_remaining': 2 - transfer_count,
    })