import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider, useAppContext } from "./context/AppContext";
import Login from "./pages/Login";
import DemoWorkflow from "./pages/DemoWorkflow";
import AppLayout from "./components/AppLayout";
import Settings from "./components/Settings";

function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAppContext();
  return isLoggedIn ? children : <Navigate to="/" replace />;
}

function ProtectedPage({ children }) {
  return <ProtectedRoute><AppLayout>{children}</AppLayout></ProtectedRoute>;
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/home" element={<ProtectedPage><DemoWorkflow /></ProtectedPage>} />
        <Route path="/settings" element={<ProtectedPage><Settings /></ProtectedPage>} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default function App() {
  return <AppProvider><AppRoutes /></AppProvider>;
}
