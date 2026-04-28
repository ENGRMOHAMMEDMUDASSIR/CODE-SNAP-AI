// frontend/static/js/script.js
let currentAnalysis = null;

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyze-btn');
    const repoUrlInput = document.getElementById('repo-url');
    
    mermaid.initialize({ startOnLoad: false, theme: 'dark' });
    
    analyzeBtn.addEventListener('click', () => analyzeRepository());
    repoUrlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') analyzeRepository();
    });
});

async function analyzeRepository() {
    const repoUrl = document.getElementById('repo-url').value.trim();
    
    if (!repoUrl) {
        showError('Please enter a GitHub repository URL');
        return;
    }
    
    if (!repoUrl.includes('github.com')) {
        showError('Please enter a valid GitHub URL (e.g., https://github.com/owner/repo)');
        return;
    }
    
    showLoading(true);
    hideError();
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_url: repoUrl })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        
        const result = await response.json();
        currentAnalysis = result.data;
        
        displayResults(result.data);
        
        if (result.cached) {
            showNotification('Results loaded from cache', 'info');
        }
        
    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
}

function displayResults(data) {
    document.getElementById('results').classList.remove('hidden');
    
    document.getElementById('repo-name').textContent = data.repo_name;
    
    const techStackDiv = document.getElementById('tech-stack');
    techStackDiv.innerHTML = data.tech_stack.map(tech => 
        `<span class="tech-badge">${tech}</span>`
    ).join('');
    
    document.getElementById('description').innerHTML = `
        <h3>📖 Description</h3>
        <p>${data.description}</p>
        <p><strong>Architecture Pattern:</strong> ${data.architecture_pattern}</p>
        <p><strong>Analyzed:</strong> ${new Date(data.analyzed_at).toLocaleString()}</p>
    `;
    
    const folderStructure = document.getElementById('folder-structure');
    folderStructure.innerHTML = '<h3>📁 Folder Structure</h3>';
    for (const [folder, explanation] of Object.entries(data.folder_structure_explanation)) {
        folderStructure.innerHTML += `
            <div class="folder-item">
                <strong>${folder}</strong>
                <p>${explanation}</p>
            </div>
        `;
    }
    
    const diagramElement = document.getElementById('mermaid-diagram');
    diagramElement.textContent = data.architecture_diagram;
    mermaid.contentLoaded();
    
    const onboardingSteps = document.getElementById('onboarding-steps');
    onboardingSteps.innerHTML = '<h3>🚀 Onboarding Guide</h3>';
    data.onboarding_guide.forEach(step => {
        onboardingSteps.innerHTML += `
            <div class="onboarding-step">
                <div class="step-title">${step.step}. ${step.title}</div>
                <div>${step.description}</div>
                ${step.commands ? `
                    <div class="step-commands">
                        ${step.commands.map(cmd => `<div>💰 ${cmd}</div>`).join('')}
                    </div>
                ` : ''}
                ${step.code_sample ? `
                    <div class="step-commands">
                        <pre><code>${step.code_sample}</code></pre>
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    const keyFilesDiv = document.getElementById('key-files');
    keyFilesDiv.innerHTML = '<h3>📄 Key Files Explained</h3>';
    for (const [file, explanation] of Object.entries(data.key_files_explained)) {
        keyFilesDiv.innerHTML += `
            <div class="onboarding-step">
                <strong>${file}</strong>
                <p>${explanation}</p>
            </div>
        `;
    }
    
    const entryPointsDiv = document.getElementById('entry-points');
    entryPointsDiv.innerHTML = '<h3>🎯 Entry Points</h3>';
    entryPointsDiv.innerHTML += `
        <div class="onboarding-step">
            <p>Start here: <strong>${data.entry_points.join(', ') || 'Check README.md'}</strong></p>
        </div>
    `;
    
    setupTabs();
}

function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            tabs.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            document.getElementById(tabId).classList.add('active');
        });
    });
}

function showLoading(show) {
    const loadingDiv = document.getElementById('loading');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    if (show) {
        loadingDiv.classList.remove('hidden');
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '⏳ Analyzing...';
    } else {
        loadingDiv.classList.add('hidden');
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🔍 Analyze Repository';
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    const errorDiv = document.getElementById('error-message');
    errorDiv.classList.add('hidden');
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}