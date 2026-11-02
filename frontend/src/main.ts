import { mount } from "svelte";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "./style.css";
import "./lib/styles/layout.css";
import "./lib/styles/explorer.css";
import "./lib/styles/manage.css";
import "./lib/styles/responsive.css";
import App from "./App.svelte";

mount(App, { target: document.getElementById("app")! });
