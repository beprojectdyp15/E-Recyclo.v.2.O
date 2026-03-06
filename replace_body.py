import re

filepath = r'b:\E-RECYCLO\RECYCLO.v2.O\templates\accounts\complete_collector_profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacement_html = """{% block page_content %}
<div class="max-w-7xl mx-auto space-y-8 pb-24 px-4 sm:px-6 mt-6">
    
    <!-- ── PROGRESS HEADER ── -->
    <div class="premium-card p-6 md:p-8 flex flex-col md:flex-row items-center gap-6">
        <div class="flex-1 space-y-2 text-center md:text-left">
            <h1 class="text-2xl font-black text-slate-800 dark:text-white">Collector Profile Authentication</h1>
            <p class="text-sm font-semibold text-slate-500 uppercase tracking-wider">Finalize your logistics identity for operational approval</p>
        </div>
        
        <div class="flex items-center gap-6 w-full md:w-auto">
            <div class="flex-1 md:w-64">
                <div class="flex justify-between mb-2">
                    <span class="text-xs font-black text-slate-400 uppercase tracking-widest">Profile Score</span>
                    <span class="text-xs font-black text-primary uppercase">{{ completion_percentage }}%</span>
                </div>
                <div class="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all duration-1000 {% if completion_percentage == 100 %}bg-primary{% else %}progress-shimmer{% endif %}" 
                         style="width: {{ completion_percentage }}%"></div>
                </div>
            </div>
            <div class="size-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <span class="material-symbols-outlined text-3xl">verified</span>
            </div>
        </div>
    </div>

    <form method="POST" enctype="multipart/form-data" id="collectorProfileForm" class="space-y-8" novalidate>
        {% csrf_token %}
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            <!-- LEFT: BASIC DETAILS -->
            <div class="premium-card p-8 space-y-8">
                <div class="flex items-center gap-4">
                    <div class="section-icon">
                        <span class="material-symbols-outlined">person</span>
                    </div>
                    <div>
                        <h3 class="text-sm font-black text-slate-800 dark:text-white uppercase tracking-widest">Basic Details *</h3>
                        <p class="text-[10px] font-bold text-slate-400 uppercase">Primary Contact Info</p>
                    </div>
                </div>

                <div class="space-y-8">
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Birth Date *</label>
                        <input type="text" name="date_of_birth" id="id_date_of_birth" value="{{ form.date_of_birth.value|date:'Y-m-d'|default:'' }}" 
                               class="input-premium" placeholder="Select Date" readonly>
                        <p id="dobError" class="text-[9px] font-bold text-red-500 uppercase px-1 hidden">Must be 18+ years old</p>
                    </div>

                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">Full Address *</label>
                        <textarea name="address" class="input-premium !py-4 min-h-[100px] resize-none" placeholder="Enter complete home/operational address..." required>{{ form.address.value|default:'' }}</textarea>
                    </div>
                </div>
            </div>

            <!-- RIGHT: VEHICLE PROFILE -->
            <div class="premium-card p-8 space-y-8">
                <div class="flex items-center gap-4">
                    <div class="section-icon bg-blue-500/10 text-blue-500">
                        <span class="material-symbols-outlined">local_shipping</span>
                    </div>
                    <div>
                        <h3 class="text-sm font-black text-slate-800 dark:text-white uppercase tracking-widest">Active Vehicle *</h3>
                        <p class="text-[10px] font-bold text-slate-400 uppercase">Registered operations fleet</p>
                    </div>
                </div>

                <div class="space-y-6">
                    <div class="space-y-2">
                        <label class="field-label">Vehicle Registration Number *</label>
                        <input type="text" name="vehicle_number" id="id_vehicle_number" value="{{ form.vehicle_number.value|default:'' }}" class="input-premium uppercase" placeholder="e.g. MH12AB1234">
                    </div>

                    <!-- Custom Dropdown Container -->
                    <div class="custom-select-wrapper mb-0">
                        <label class="field-label">Vehicle Type *</label>
                        <div class="custom-select-box" style="height: 53px; border-radius: 1rem;" onclick="toggleCustomSelect()">
                            <span class="material-symbols-outlined text-blue-500 text-xl">directions_car</span>
                            <span id="selected_vehicle_label" class="flex-1 uppercase text-[10px]">{% for val, label in form.fields.vehicle_type.choices %}{% if form.vehicle_type.value == val %}{{ label }}{% endif %}{% endfor %}</span>
                            <span class="material-symbols-outlined text-slate-400">expand_more</span>
                        </div>
                        
                        <select name="vehicle_type" id="id_vehicle_type" class="hidden">
                            {% for val, label in form.fields.vehicle_type.choices %}
                            <option value="{{ val }}" {% if form.vehicle_type.value == val %}selected{% endif %}>{{ label }}</option>
                            {% endfor %}
                        </select>

                        <!-- Options Dropdown -->
                        <div id="custom-options" class="absolute z-50 w-full mt-2 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl shadow-xl overflow-hidden hidden transition-all">
                            {% for val, label in form.fields.vehicle_type.choices %}
                                {% if val %}
                                <div class="px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer text-[10px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-widest transition-colors flex items-center gap-3"
                                     onclick="selectVehicleOption('{{ val }}', '{{ label }}')">
                                     <div class="size-2 rounded-full {% if form.vehicle_type.value == val %}bg-blue-500{% else %}bg-transparent border border-slate-300{% endif %}"></div>
                                     {{ label }}
                                </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>

            <!-- FULL WIDTH: COMPLIANCE ASSETS -->
            <div class="lg:col-span-2 premium-card p-8 space-y-8">
                <div class="flex items-center gap-4">
                    <div class="section-icon bg-amber-500/10 text-amber-500">
                        <span class="material-symbols-outlined">description</span>
                    </div>
                    <div>
                        <h3 class="text-sm font-black text-slate-800 dark:text-white uppercase tracking-widest">Compliance Assets</h3>
                        <p class="text-[10px] font-bold text-slate-400 uppercase">Regulatory vault & identification</p>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
                    
                    <!-- MODULE 01: DRIVING LICENSE -->
                    <div class="module-card">
                        <h2 class="module-title uppercase">Driving License <span class="text-rose-500">*</span></h2>
                        <p class="module-desc">Operator Authenticity Check</p>
                        
                        <div id="license_preview_btn" class="view-badge {% if not form.instance.driving_license %}hidden{% endif %}" onclick="previewDoc('{% if form.instance.driving_license %}{{ form.instance.driving_license.url }}{% endif %}'); event.stopPropagation();">
                            <span class="material-symbols-outlined text-[20px]">visibility</span>
                        </div>

                        <div class="flex flex-col gap-6 mt-8">
                            <div class="space-y-1">
                                <label class="field-label">DL Number <span class="text-rose-500">*</span></label>
                                <input type="text" name="license_number" id="id_license_number" 
                                       value="{{ form.license_number.value|default:'' }}" 
                                       class="input-module" placeholder="DL Number">
                            </div>
                            <div class="space-y-1">
                                <label class="field-label">Upload <span class="text-rose-500">*</span></label>
                                <div class="upload-button {% if form.instance.driving_license %}secured{% endif %}" onclick="triggerFileInput('id_driving_license')">
                                    <input type="file" name="driving_license" id="id_driving_license" class="hidden" onchange="handleFileChange(this, 'license_status')">
                                    <span id="license_status" class="uppercase">{% if form.instance.driving_license %}✓{% else %}Select{% endif %}</span>
                                </div>
                                <p class="text-[9px] font-bold text-slate-400 uppercase mt-2 leading-tight">PDF, JPG, PNG <br> Max 250KB</p>
                            </div>
                        </div>
                    </div>

                    <!-- MODULE 02: AADHAAR -->
                    <div class="module-card">
                        <h2 class="module-title uppercase">Aadhaar Vault <span class="text-rose-500">*</span></h2>
                        <p class="module-desc">Registry Master Key</p>

                        <div id="aadhaar_preview_btn" class="view-badge {% if not form.instance.aadhaar_card %}hidden{% endif %}" onclick="previewDoc('{% if form.instance.aadhaar_card %}{{ form.instance.aadhaar_card.url }}{% endif %}'); event.stopPropagation();">
                            <span class="material-symbols-outlined text-[20px]">visibility</span>
                        </div>

                        <div class="flex flex-col gap-6 mt-8">
                            <div class="space-y-1">
                                <label class="field-label">UID / Aadhaar <span class="text-rose-500">*</span></label>
                                <input type="text" name="aadhaar_number" id="id_aadhaar_number" maxlength="12" 
                                       pattern="[2-9]{1}[0-9]{11}"
                                       oninput="this.value = this.value.replace(/[^0-9]/g, '');"
                                       value="{{ form.aadhaar_number.value|default:'' }}" 
                                       class="input-module" placeholder="12-digit UID No">
                            </div>
                            <div class="space-y-1">
                                <label class="field-label">Upload <span class="text-rose-500">*</span></label>
                                <div class="upload-button {% if form.instance.aadhaar_card %}secured{% endif %}" onclick="triggerFileInput('id_aadhaar_card')">
                                    <input type="file" name="aadhaar_card" id="id_aadhaar_card" class="hidden" onchange="handleFileChange(this, 'aadhaar_status')">
                                    <span id="aadhaar_status" class="uppercase">{% if form.instance.aadhaar_card %}✓{% else %}Select{% endif %}</span>
                                </div>
                                <p class="text-[9px] font-bold text-slate-400 uppercase mt-2 leading-tight">PDF, JPG, PNG <br> Max 250KB</p>
                            </div>
                        </div>
                    </div>

                    <!-- MODULE 03: VEHICLE RC -->
                    <div class="module-card">
                        <h2 class="module-title uppercase">Vehicle RC Link <span class="text-rose-500">*</span></h2>
                        <p class="module-desc">Fleet Legitimacy Validation</p>

                        <div id="rc_preview_btn" class="view-badge {% if not form.instance.vehicle_rc %}hidden{% endif %}" onclick="previewDoc('{% if form.instance.vehicle_rc %}{{ form.instance.vehicle_rc.url }}{% endif %}'); event.stopPropagation();">
                            <span class="material-symbols-outlined text-[20px]">visibility</span>
                        </div>

                        <div class="flex flex-col gap-6 mt-8">
                            <div class="space-y-1">
                                <label class="field-label">RC Number <span class="text-rose-500">*</span></label>
                                <input type="text" name="vehicle_rc_number" id="id_vehicle_rc_number" 
                                       value="{{ form.vehicle_rc_number.value|default:'' }}" 
                                       class="input-module" placeholder="RC Number">
                            </div>
                            <div class="space-y-1">
                                <label class="field-label">Upload <span class="text-rose-500">*</span></label>
                                <div class="upload-button {% if form.instance.vehicle_rc %}secured{% endif %}" onclick="triggerFileInput('id_vehicle_rc')">
                                    <input type="file" name="vehicle_rc" id="id_vehicle_rc" class="hidden" onchange="handleFileChange(this, 'rc_status')">
                                    <span id="rc_status" class="uppercase">{% if form.instance.vehicle_rc %}✓{% else %}Select{% endif %}</span>
                                </div>
                                <p class="text-[9px] font-bold text-slate-400 uppercase mt-2 leading-tight">PDF, JPG, PNG <br> Max 250KB</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ── FINALIZATION ── -->
        <div id="form-actions-container" class="flex flex-col md:flex-row items-center justify-center gap-6 pt-10">
            {% if profile_completion.approval_status == 'approved' %}
                <div class="flex flex-col items-center gap-4 py-8 px-12 bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 rounded-3xl text-emerald-600">
                    <div class="size-16 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center mb-2">
                        <span class="material-symbols-outlined text-3xl font-variation-settings-'FILL'-1">verified</span>
                    </div>
                    <h3 class="text-sm font-black uppercase tracking-[0.2em]">Security Clearance Granted</h3>
                    <p class="text-[10px] font-bold text-emerald-500/80 uppercase tracking-widest text-center">Your fleet profile has been verified and authorized. No further actions required.</p>
                </div>
            {% elif profile_completion.approval_status == 'pending' %}
                <div class="flex flex-col items-center gap-4 py-8 px-12 bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/30 rounded-3xl text-amber-600">
                    <div class="size-16 rounded-full bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center mb-2">
                        <span class="material-symbols-outlined text-3xl animate-pulse">hourglass_top</span>
                    </div>
                    <h3 class="text-sm font-black uppercase tracking-[0.2em]">Profile submitted for approval</h3>
                    <p class="text-[10px] font-bold text-amber-500/80 uppercase tracking-widest text-center">Your credentials are currently in the regulatory vault for admin verification.</p>
                </div>
            {% else %}
                <button type="submit" name="action" value="save_draft" id="btn-save-draft" formnovalidate class="flex items-center gap-3 px-10 py-5 bg-slate-800 dark:bg-slate-900/20 text-slate-700 dark:text-slate-300 rounded-xl transition-all hover:scale-[1.02] active:scale-[0.98] border border-slate-200/50 dark:border-slate-700">
                    <span class="material-symbols-outlined text-lg text-slate-200">save</span>
                    <span class="text-xs font-semibold text-white uppercase tracking-[0.2em]">Save Profile Progress</span>
                </button>

                <button type="submit" name="action" value="submit" id="btn-submit-main" class="group relative px-12 py-5 bg-primary text-white rounded-xl overflow-hidden transition-all hover:scale-[1.02] active:scale-[0.98] shadow-2xl shadow-emerald-200/50 dark:shadow-none">
                    <div class="relative z-10 flex items-center gap-3">
                        <span class="text-xs font-black uppercase tracking-[0.2em]">{% if profile_completion.approval_status == 'rejected' %}Resubmit Core{% else %}Authorize Verification{% endif %}</span>
                        <span class="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">send</span>
                    </div>
                </button>
            {% endif %}
        </div>

        <div id="submission-message" class="hidden flex-col items-center gap-4 py-8 px-12 bg-primary/5 border border-primary/20 rounded-3xl text-primary pt-10 mt-10">
            <div class="size-16 rounded-full bg-primary/10 flex items-center justify-center mb-2">
                <span class="material-symbols-outlined text-3xl animate-bounce">rocket_launch</span>
            </div>
            <h3 class="text-sm font-black uppercase tracking-[0.2em]">Processing Security Submission</h3>
            <p class="text-[10px] font-bold text-primary/80 uppercase tracking-widest text-center">Verifying credentials and synchronizing with the central registry...</p>
        </div>

        <div class="flex justify-center mt-6">
            <a href="{% url 'collector:dashboard' %}" class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest hover:text-rose-500 transition-colors">
                Cancel and go back
            </a>
        </div>
    </form>
</div>

<!-- Modal for Document Preview -->
<div id="previewModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4">
    <div class="absolute inset-0 modal-backdrop" onclick="closeModal()"></div>
    <div class="relative bg-white dark:bg-slate-900 w-full max-w-4xl max-h-[90vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl">
        <div class="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <h3 class="text-xs font-black uppercase text-slate-500 tracking-widest">Credential Artifact</h3>
            <button onclick="closeModal()" class="size-8 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center transition-colors">
                <span class="material-symbols-outlined text-[18px]">close</span>
            </button>
        </div>
        <div class="relative flex-1 bg-slate-50 dark:bg-slate-900/50 p-6 overflow-hidden flex items-center justify-center min-h-[400px]">
            <img id="modalImage" src="" class="max-w-full max-h-[70vh] object-contain hidden shadow-lg rounded-xl">
            <iframe id="modalPdf" src="" class="w-full h-[70vh] hidden rounded-xl shadow-lg border-0 bg-white"></iframe>
        </div>
    </div>
</div>
{% endblock %}"""

out_content = re.sub(r'{% block page_content %}.*?{% endblock %}', replacement_html, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(out_content)

print(f"File updated correctly.")
