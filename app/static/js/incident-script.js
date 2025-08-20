const API_BASE_URL = '/incidents';

let incidents = [];
let currentIncidentId = null;

const elements = {
    loading: document.getElementById('loading'),
    errorMessage: document.getElementById('errorMessage'),
    successMessage: document.getElementById('successMessage'),
    incidentsList: document.getElementById('incidentsList'),
    modal: document.getElementById('modal'),
    deleteModal: document.getElementById('deleteModal'),
    modalTitle: document.getElementById('modalTitle'),
    incidentForm: document.getElementById('incidentForm'),
    createBtn: document.getElementById('createBtn'),
    closeModal: document.getElementById('closeModal'),
    cancelBtn: document.getElementById('cancelBtn'),
    submitBtn: document.getElementById('submitBtn'),
    closeDeleteModal: document.getElementById('closeDeleteModal'),
    cancelDeleteBtn: document.getElementById('cancelDeleteBtn'),
    confirmDeleteBtn: document.getElementById('confirmDeleteBtn')
};

function showLoading() {
    elements.loading.classList.remove('hidden');
}

function hideLoading() {
    elements.loading.classList.add('hidden');
}

function showError(message) {
    const errorText = elements.errorMessage.querySelector('.error-text');
    errorText.textContent = message;
    elements.errorMessage.classList.remove('hidden');
    setTimeout(() => {
        elements.errorMessage.classList.add('hidden');
    }, 5000);
}

function showSuccess(message) {
    const successText = elements.successMessage.querySelector('.success-text');
    successText.textContent = message;
    elements.successMessage.classList.remove('hidden');
    setTimeout(() => {
        elements.successMessage.classList.add('hidden');
    }, 3000);
}

function formatDateTime(dateTimeString) {
    return new Date(dateTimeString).toLocaleString();
}

function formatDateTimeForInput(dateTimeString) {
    if (!dateTimeString) return '';

    const date = new Date(dateTimeString);

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

async function fetchIncidents() {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/list`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        incidents = await response.json();
        renderIncidents();
    } catch (error) {
        console.error('Error fetching incidents:', error);
        showError('Failed to load incidents. Please try again.');
    } finally {
        hideLoading();
    }
}

async function createIncident(incidentData) {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/incident`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(incidentData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        showSuccess('Инцидент создан успешно!');
        closeModal();
        await fetchIncidents();
    } catch (error) {
        console.error('Error creating incident:', error);
        showError('Ошибка при создании инцидента. Пожалуйста, попробуйте еще раз.');
    } finally{
        hideLoading();
    }
}

async function updateIncident(incidentData) {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/incident/update`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(incidentData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        showSuccess('Инцидент обновлен успешно!');
        closeModal();
        await fetchIncidents();
    } catch (error) {
        console.error('Error updating incident:', error);
        showError('Ошибка при редактировании инцидента. Пожалуйста, попробуйте еще раз.');
    } finally {
        hideLoading();
    }
}

async function deleteIncident(incidentId) {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/incident?incident_id=${incidentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        showSuccess('Инцидент удален успешно!');
        closeDeleteModal();
        await fetchIncidents();
    } catch (error) {
        console.error('Error deleting incident:', error);
        showError('Ошибка при удалении инцидента. Пожалуйста, попробуйте еще раз.');
    } finally {
        hideLoading();
    }
}

function renderIncidents() {
    if (incidents.length === 0) {
        elements.incidentsList.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #718096;">
                <p style="font-size: 1.2rem; margin-bottom: 10px;">Инцидентов не обнаружено</p>
                <p>Создайте свой первый инцидент!</p>
            </div>
        `;
        return;
    }

    elements.incidentsList.innerHTML = incidents.map(incident => `
        <div class="incident-card">
            <div class="incident-header">
                <div>
                    <div class="incident-title">${escapeHtml(incident.incident_name)}</div>
                    <div class="incident-id">ID: ${incident.incident_id}</div>
                </div>
                <div class="incident-actions">
                    <button class="btn btn-edit" onclick="editIncident(${incident.incident_id})">Редактировать</button>
                    <button class="btn btn-delete" onclick="confirmDelete(${incident.incident_id})">Удалить</button>
                </div>
            </div>
            <div class="incident-description">${escapeHtml(incident.incident_description)}</div>
            <div class="incident-script">${escapeHtml(incident.incident_script)}</div>
            <div class="incident-dates">
                <div class="date-info">
                    <div class="date-label">Время начала недоступности</div>
                    <div class="date-value">${formatDateTime(incident.incident_startdate)}</div>
                </div>
                <div class="date-info">
                    <div class="date-label">Время окончания недоступности</div>
                    <div class="date-value">${formatDateTime(incident.incident_enddate)}</div>
                </div>
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openModal(title = 'Создание') {
    elements.modalTitle.textContent = title;
    elements.modal.classList.remove('hidden');
    elements.submitBtn.textContent = title.includes('Редактирование') ? 'Редактировать инцидент' : 'Создать инцидент';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    elements.modal.classList.add('hidden');
    elements.incidentForm.reset();
    currentIncidentId = null;
    document.body.style.overflow = 'auto';
}

function openDeleteModal() {
    elements.deleteModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeDeleteModal() {
    elements.deleteModal.classList.add('hidden');
    currentIncidentId = null;
    document.body.style.overflow = 'auto';
}

function editIncident(incidentId) {
    const incident = incidents.find(i => i.incident_id === incidentId);
    if (!incident) return;

    currentIncidentId = incidentId;
    
    document.getElementById('incidentId').value = incident.incident_id;
    document.getElementById('incidentName').value = incident.incident_name;
    document.getElementById('incidentDescription').value = incident.incident_description;
    document.getElementById('incidentScript').value = incident.incident_script;
    document.getElementById('startDate').value = formatDateTimeForInput(incident.incident_startdate);
    document.getElementById('endDate').value = formatDateTimeForInput(incident.incident_enddate);

    openModal('Редактирование');
}

function confirmDelete(incidentId) {
    currentIncidentId = incidentId;
    openDeleteModal();
}

function initializeEventListeners() {
    elements.createBtn.addEventListener('click', () => {
        openModal();
    });

    elements.closeModal.addEventListener('click', closeModal);
    elements.cancelBtn.addEventListener('click', closeModal);

    elements.closeDeleteModal.addEventListener('click', closeDeleteModal);
    elements.cancelDeleteBtn.addEventListener('click', closeDeleteModal);

    elements.confirmDeleteBtn.addEventListener('click', () => {
        if (currentIncidentId) {
            deleteIncident(currentIncidentId);
        }
    });

    elements.incidentForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const incidentData = {
            incident_name: document.getElementById('incidentName').value.trim(),
            incident_description: document.getElementById('incidentDescription').value.trim(),
            incident_script: document.getElementById('incidentScript').value.trim(),
            incident_startdate: document.getElementById('startDate').value,
            incident_enddate: document.getElementById('endDate').value
        };

        if (!incidentData.incident_name || !incidentData.incident_description || !incidentData.incident_script || !incidentData.incident_startdate || !incidentData.incident_enddate) {
            showError('Please fill in all required fields.');
            return;
        }

        if (new Date(incidentData.incident_startdate) >= new Date(incidentData.incident_enddate)) {
            showError('End date must be after start date.');
            return;
        }

        if (currentIncidentId) {
            incidentData.incident_id = currentIncidentId;
            await updateIncident(incidentData);
        } else {
            await createIncident(incidentData);
        }
    });

    elements.modal.addEventListener('click', (e) => {
        if (e.target === elements.modal) {
            closeModal();
        }
    });

    elements.deleteModal.addEventListener('click', (e) => {
        if (e.target === elements.deleteModal) {
            closeDeleteModal();
        }
    });

    const errorClose = document.querySelector('.error-close');
    const successClose = document.querySelector('.success-close');
    
    if (errorClose) {
        errorClose.addEventListener('click', () => {
            elements.errorMessage.classList.add('hidden');
        });
    }

    if (successClose) {
        successClose.addEventListener('click', () => {
            elements.successMessage.classList.add('hidden');
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!elements.modal.classList.contains('hidden')) {
                closeModal();
            }
            if (!elements.deleteModal.classList.contains('hidden')) {
                closeDeleteModal();
            }
        }
    });
}

window.editIncident = editIncident;
window.confirmDelete = confirmDelete;

document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    fetchIncidents();
});