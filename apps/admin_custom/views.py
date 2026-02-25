"""
Admin custom views for E-RECYCLO
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone

from apps.accounts.models import Account, ProfileCompletion
from apps.client.models import PhotoPost
from apps.payments.models import WithdrawalRequest


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_superuser or user.is_admin)


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard"""
    
    # Get stats
    total_users = Account.objects.filter(is_superuser=False).count()
    pending_approvals = ProfileCompletion.objects.filter(
        approval_status='pending'
    ).count()
    total_uploads = PhotoPost.objects.count()
    pending_withdrawals = WithdrawalRequest.objects.filter(
        status='pending'
    ).count()
    
    # Recent activity
    recent_uploads = PhotoPost.objects.all().order_by('-created_at')[:5]
    recent_users = Account.objects.filter(
        is_superuser=False
    ).order_by('-date_joined')[:5]
    
    context = {
        'total_users': total_users,
        'pending_approvals': pending_approvals,
        'total_uploads': total_uploads,
        'pending_withdrawals': pending_withdrawals,
        'recent_uploads': recent_uploads,
        'recent_users': recent_users,
    }
    
    return render(request, 'admin_custom/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def pending_approvals(request):
    """View pending profile approvals"""
    
    approvals = ProfileCompletion.objects.filter(
        approval_status='pending',
        profile_submitted=True
    ).select_related('user').order_by('-submitted_at')
    
    context = {
        'approvals': approvals,
    }
    
    return render(request, 'admin_custom/pending_approvals.html', context)


@login_required
@user_passes_test(is_admin)
def approve_profile(request, pk):
    """Approve a profile"""
    
    profile = get_object_or_404(ProfileCompletion, pk=pk)
    
    if request.method == 'POST':
        profile.approval_status = 'approved'
        profile.admin_reviewed = True
        profile.admin_reviewed_by = request.user
        profile.approved_at = timezone.now()
        profile.admin_remarks = request.POST.get('remarks', '')
        profile.save()
        
        # Send approval email
        from apps.notifications.utils import send_profile_approved_email
        send_profile_approved_email(profile.user)
        
        messages.success(request, f'Profile approved for {profile.user.email}')
        return redirect('admin_custom:pending_approvals')
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'admin_custom/approve_profile.html', context)


@login_required
@user_passes_test(is_admin)
def reject_profile(request, pk):
    """Reject a profile"""
    
    profile = get_object_or_404(ProfileCompletion, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('admin_custom:pending_approvals')
        
        profile.approval_status = 'rejected'
        profile.admin_reviewed = True
        profile.admin_reviewed_by = request.user
        profile.admin_remarks = reason
        profile.save()
        
        # Send rejection email
        from apps.notifications.utils import send_profile_rejected_email
        send_profile_rejected_email(profile.user, reason)
        
        messages.success(request, f'Profile rejected for {profile.user.email}')
        return redirect('admin_custom:pending_approvals')
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'admin_custom/reject_profile.html', context)


@login_required
@user_passes_test(is_admin)
def users(request):
    """View all users"""
    
    role = request.GET.get('role', '')
    
    users = Account.objects.filter(is_superuser=False)
    
    if role == 'client':
        users = users.filter(is_client=True)
    elif role == 'vendor':
        users = users.filter(is_vendor=True)
    elif role == 'collector':
        users = users.filter(is_collector=True)
    
    users = users.order_by('-date_joined')
    
    # Get counts
    counts = {
        'all': Account.objects.filter(is_superuser=False).count(),
        'clients': Account.objects.filter(is_client=True).count(),
        'vendors': Account.objects.filter(is_vendor=True).count(),
        'collectors': Account.objects.filter(is_collector=True).count(),
    }
    
    context = {
        'users': users,
        'role': role,
        'counts': counts,
    }
    
    return render(request, 'admin_custom/users.html', context)


@login_required
@user_passes_test(is_admin)
def analytics(request):
    """View analytics"""
    
    # Monthly stats
    current_year = timezone.now().year
    
    monthly_uploads = []
    monthly_users = []
    
    for month in range(1, 13):
        uploads = PhotoPost.objects.filter(
            created_at__year=current_year,
            created_at__month=month
        ).count()
        
        new_users = Account.objects.filter(
            date_joined__year=current_year,
            date_joined__month=month,
            is_superuser=False
        ).count()
        
        monthly_uploads.append({'month': month, 'count': uploads})
        monthly_users.append({'month': month, 'count': new_users})
    
    # Overall stats
    total_value = PhotoPost.objects.filter(
        status='completed'
    ).aggregate(total=Sum('vendor_final_value'))['total']
    
    context = {
        'monthly_uploads': monthly_uploads,
        'monthly_users': monthly_users,
        'total_value': total_value,
        'current_year': current_year,
    }
    
    return render(request, 'admin_custom/analytics.html', context)