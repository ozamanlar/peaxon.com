// privacy.js
function checkPrivacyConsent() {
    if (!localStorage.getItem('peaxon_consent')) {
        const consentHTML = `
            <div id="consent-popup" style="position:fixed; bottom:0; width:100%; background:rgba(10,10,20,0.95); border-top:2px solid #00f3ff; color:white; padding:20px; text-align:center; z-index:10000; font-family:'Rajdhani';">
                <p style="margin-bottom:15px; font-size:0.9rem;">
                    <strong>[PRIVACY PROTOCOL]</strong> Peaxon uses terminal logs for security monitoring and analytical reporting (KVKK/GDPR compliant). 
                    By continuing, you consent to encrypted telemetry reporting via Telegram Node.
                </p>
                <button onclick="acceptConsent()" style="background:#00f3ff; color:black; border:none; padding:10px 30px; cursor:pointer; font-family:'Orbitron'; font-weight:bold;">I ACCEPT</button>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', consentHTML);
    } else {
        if (typeof peaxonFinalLogger === "function") peaxonFinalLogger();
        if (typeof peaxonHorizonLogger === "function") peaxonHorizonLogger();
    }
}

function acceptConsent() {
    localStorage.setItem('peaxon_consent', 'true');
    document.getElementById('consent-popup').remove();
    location.reload(); // Sayfayı yenileyerek logger'ı tetikle
}

window.onload = checkPrivacyConsent;