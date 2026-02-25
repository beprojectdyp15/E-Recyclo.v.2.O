import os

files = [
    'templates/base.html',
    'templates/home.html',
    'templates/accounts/register.html',
    'templates/accounts/verify_email.html',
    'templates/accounts/login.html',
    'templates/accounts/profile.html',
    'templates/accounts/edit_profile.html',
    'templates/accounts/complete_vendor_profile.html',
    'templates/accounts/complete_collector_profile.html',
    'templates/client/dashboard.html',
    'templates/client/upload_ewaste.html',
    'templates/client/my_uploads.html',
    'templates/client/upload_detail.html',
    'templates/client/wallet.html',
    'templates/client/collection_centers.html',
    'templates/client/bulk_pickup.html',
]

for filepath in files:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('{% block content %}', '{% block page_content %}')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed: {filepath}")

print("\n🎉 All done! Refresh browser now!")