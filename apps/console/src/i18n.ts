import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      app_title: 'Verge — Operator Console',
      board: 'BOARD',
      replay: 'REPLAY',
      fleet: 'FLEET',
      audit: 'AUDIT',
      config: 'CONFIG',
      handover: 'HANDOVER',
      live: 'LIVE',
      shadow: 'SHADOW',
      // States
      'new': 'New',
      'acknowledged': 'Acknowledged',
      'assigned': 'Assigned',
      'in-progress': 'In Progress',
      'escalated': 'Escalated',
      'snoozed': 'Snoozed',
      'resolved': 'Resolved',
      'closed': 'Closed',
      'suppressed-as-duplicate': 'Suppressed',
      'reopened': 'Reopened',
    },
  },
  hi: {
    translation: {
      app_title: 'वर्ज — ऑपरेटर कंसोल',
      board: 'बोर्ड',
      replay: 'रीप्ले',
      fleet: 'बेड़ा',
      audit: 'ऑडिट',
      config: 'कॉन्फ़िगर',
      handover: 'हैंडओवर',
      live: 'लाइव',
      shadow: 'शैडो',
      // States
      'new': 'नया',
      'acknowledged': 'स्वीकृत',
      'assigned': 'सौंपा गया',
      'in-progress': 'प्रगति पर',
      'escalated': 'बढ़ाया गया',
      'snoozed': 'स्नूज़',
      'resolved': 'समाधान',
      'closed': 'बंद',
      'suppressed-as-duplicate': 'दबाया गया',
      'reopened': 'पुनः खोला गया',
    },
  },
  ta: {
    translation: {
      app_title: 'வெர்ஜ் — ஆபரேட்டர் கன்சோல்',
      board: 'பலகை',
      replay: 'மீள் இயக்கம்',
      fleet: 'கடற்படை',
      audit: 'தணிக்கை',
      config: 'அமைப்பு',
      handover: 'ஒப்படைப்பு',
      live: 'நேரலை',
      shadow: 'நிழல்',
      // States
      'new': 'புதியது',
      'acknowledged': 'ஏற்கப்பட்டது',
      'assigned': 'ஒதுக்கப்பட்டது',
      'in-progress': 'செயலில்',
      'escalated': 'மேம்படுத்தப்பட்டது',
      'snoozed': 'உறக்கம்',
      'resolved': 'தீர்க்கப்பட்டது',
      'closed': 'மூடப்பட்டது',
      'suppressed-as-duplicate': 'தடுக்கப்பட்டது',
      'reopened': 'மீண்டும் திறக்கப்பட்டது',
    },
  },
  te: {
    translation: {
      app_title: 'వెర్జ్ — ఆపరేటర్ కన్సోల్',
      board: 'బోర్డు',
      replay: 'రీప్లే',
      fleet: 'ఫ్లీట్',
      audit: 'ఆడిట్',
      config: 'ఆకృతీకరణ',
      handover: 'హ్యాండోవర్',
      live: 'లైవ్',
      shadow: 'షాడో',
      // States
      'new': 'కొత్తది',
      'acknowledged': 'అంగీకరించబడింది',
      'assigned': 'అప్పగించబడింది',
      'in-progress': 'ప్రగతిలో ఉంది',
      'escalated': 'పెంచబడింది',
      'snoozed': 'స్నూజ్',
      'resolved': 'పరిష్కరించబడింది',
      'closed': 'మూసివేయబడింది',
      'suppressed-as-duplicate': 'అణచివేయబడింది',
      'reopened': 'తిరిగి తెరవబడింది',
    },
  },
  kn: {
    translation: {
      app_title: 'ವರ್ಜ್ — ಆಪರೇಟರ್ ಕನ್ಸೋಲ್',
      board: 'ಬೋರ್ಡ್',
      replay: 'ಮರುಪಂದ್ಯ',
      fleet: 'ಫ್ಲೀಟ್',
      audit: 'ಆಡಿಟ್',
      config: 'ಸಂರಚನೆ',
      handover: 'ಹ್ಯಾಂಡೋವರ್',
      live: 'ಲೈವ್',
      shadow: 'ನೆರಳು',
      // States
      'new': 'ಹೊಸತು',
      'acknowledged': 'ಅಂಗೀಕರಿಸಲಾಗಿದೆ',
      'assigned': 'ನಿಯೋಜಿಸಲಾಗಿದೆ',
      'in-progress': 'ಪ್ರಗತಿಯಲ್ಲಿದೆ',
      'escalated': 'ಉಲ್ಬಣಗೊಂಡಿದೆ',
      'snoozed': 'ಸ್ನೂಜ್',
      'resolved': 'ಪರಿಹರಿಸಲಾಗಿದೆ',
      'closed': 'ಮುಚ್ಚಲಾಗಿದೆ',
      'suppressed-as-duplicate': 'ದಮನಗೊಳಿಸಲಾಗಿದೆ',
      'reopened': 'ಮತ್ತೆ ತೆರೆಯಲಾಗಿದೆ',
    },
  },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already saves from XSS
    },
  });

export default i18n;
