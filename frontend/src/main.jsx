import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import { DemoBanner } from './Demo';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/manrope/700.css';
import "./styles.css";
import "./polish.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <DemoBanner />
    <App />
  </React.StrictMode>,
);
import './localization.css';
