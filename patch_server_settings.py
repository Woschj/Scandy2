import re

file_path = 'app/templates/admin/server-settings.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

modal_html = """
<!-- Edit User Group Modal -->
<dialog id="editUserGroupModal" class="modal">
    <div class="modal-box w-11/12 max-w-2xl">
        <h3 class="font-bold text-lg mb-4">
            <i class="fas fa-edit text-primary mr-2"></i>
            Nutzergruppe bearbeiten
        </h3>

        <form id="editUserGroupForm" class="space-y-4">
            <input type="hidden" id="editGroupId" name="group_id">

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="form-control">
                    <label class="label">
                        <span class="label-text">Name <span class="text-error">*</span></span>
                    </label>
                    <input type="text" id="editGroupName" name="name" class="input input-bordered" required>
                </div>
                <div class="form-control">
                    <label class="label">
                        <span class="label-text">Beschreibung</span>
                    </label>
                    <input type="text" id="editGroupDescription" name="description" class="input input-bordered" placeholder="z.B. Teilnehmer Laptops">
                </div>
            </div>

            <div class="form-control">
                <label class="label">
                    <span class="label-text">Software-Pakete</span>
                </label>
                <div id="editSoftwareCheckboxes" class="space-y-2 max-h-40 overflow-y-auto border border-base-300 rounded-lg p-3">
                    <!-- Wird per JavaScript geladen -->
                </div>
            </div>

            <div class="modal-action">
                <button type="button" class="btn btn-ghost" onclick="closeEditUserGroupModal()">Abbrechen</button>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save mr-2"></i>Speichern
                </button>
            </div>
        </form>
    </div>
    <form method="dialog" class="modal-backdrop">
        <button>Schließen</button>
    </form>
</dialog>

<script nonce="{{ csp_nonce }}">"""

# Insert the modal HTML before the script tag
if '<script nonce="{{ csp_nonce }}">' in content:
    content = content.replace('<script nonce="{{ csp_nonce }}">', modal_html)

# Now replace the JS editUserGroup stub with the full implementation
old_js = """// Nutzergruppe bearbeiten
function editUserGroup(id) {
    // TODO: Implementiere Edit-Modal
    alert('Edit-Funktion wird noch implementiert');
}"""

new_js = """// Nutzergruppe bearbeiten - Modal öffnen
async function editUserGroup(groupId) {
    try {
        // Finde die Gruppe in der aktuellen Liste
        const group = userGroupsList.find(g => g._id === groupId);
        if (!group) {
            showToast('error', 'Nutzergruppe nicht gefunden');
            return;
        }

        // Fülle das Edit-Formular mit den aktuellen Daten
        document.getElementById('editGroupId').value = groupId;
        document.getElementById('editGroupName').value = group.name || '';
        document.getElementById('editGroupDescription').value = group.description || '';

        // Software-Checkboxes für das Edit-Modal laden
        await loadEditSoftwareCheckboxes(group.software || []);

        // Modal öffnen
        document.getElementById('editUserGroupModal').showModal();

    } catch (error) {
        console.error('Fehler beim Öffnen des Edit-Modals:', error);
        showToast('error', 'Fehler beim Laden der Gruppendaten');
    }
}

// Software-Checkboxes für Edit-Modal laden
async function loadEditSoftwareCheckboxes(selectedSoftware = []) {
    const container = document.getElementById('editSoftwareCheckboxes');
    if (!container) return;

    if (softwareList.length === 0) {
        container.innerHTML = '<p class="text-base-content/60 text-sm">Keine Software verfügbar</p>';
        return;
    }

    container.innerHTML = softwareList.map(software => `
        <label class="flex items-center gap-2 p-2 hover:bg-base-100 rounded cursor-pointer">
            <input type="checkbox" name="software" value="${software._id}" class="checkbox checkbox-sm"
                   ${selectedSoftware.includes(software._id) ? 'checked' : ''}>
            <span class="flex-1">${software.name}</span>
            ${software.version ? `<span class="text-sm text-base-content/60">v${software.version}</span>` : ''}
        </label>
    `).join('');
}

// Edit-Modal schließen
function closeEditUserGroupModal() {
    const modal = document.getElementById('editUserGroupModal');
    if (modal) modal.close();
}

// Edit-Formular Submit Handler
const editUserGroupForm = document.getElementById('editUserGroupForm');
if (editUserGroupForm) {
    editUserGroupForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const groupId = formData.get('group_id');

        if (!groupId) {
            showToast('error', 'Gruppen-ID fehlt');
            return;
        }

        try {
            const response = await fetch(`/admin/user_groups/${groupId}/edit`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                showToast('success', data.message);
                closeEditUserGroupModal();
                await loadUserGroups(); // Liste neu laden
            } else {
                showToast('error', data.message);
            }
        } catch (error) {
            console.error('Fehler beim Bearbeiten der Nutzergruppe:', error);
            showToast('error', 'Fehler beim Bearbeiten der Nutzergruppe');
        }
    });
}"""

if old_js in content:
    content = content.replace(old_js, new_js)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied.")
