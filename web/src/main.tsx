import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Dashboard from "./pages/Dashboard";
import Join from "./pages/Join";
import "./styles.css";

const Page = location.pathname.startsWith("/join") ? Join : Dashboard;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Page />
  </StrictMode>,
);
