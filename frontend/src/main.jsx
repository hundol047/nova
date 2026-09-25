import '@fontsource-variable/noto-sans-kr';
import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.jsx';
import {I18nProvider} from './i18n';
import './styles.css';
import './components/nova/nova.css';
createRoot(document.getElementById('root')).render(
  <I18nProvider>
    <App/>
  </I18nProvider>
);
