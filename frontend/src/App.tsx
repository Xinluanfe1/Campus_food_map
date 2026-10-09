import { Link, Route, Routes } from "react-router-dom";

import AppHeader from "./components/AppHeader";
import { RequireAdmin, RequireAuth } from "./components/RouteGuards";
import AdminShopsPage from "./pages/AdminShopsPage";
import LoginPage from "./pages/LoginPage";
import MapPage from "./pages/MapPage";
import RegisterPage from "./pages/RegisterPage";
import SubmitShopPage from "./pages/SubmitShopPage";
import "./styles.css";

export default function App() {
  return (
    <div className="app">
      <AppHeader />
      <Routes>
        <Route path="/" element={<MapPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/submit"
          element={
            <RequireAuth>
              <SubmitShopPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/shops"
          element={
            <RequireAdmin>
              <AdminShopsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="*"
          element={
            <main className="page">
              <p>
                页面不存在，请返回<Link to="/">首页</Link>。
              </p>
            </main>
          }
        />
      </Routes>
    </div>
  );
}
