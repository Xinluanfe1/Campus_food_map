import { useSearchParams } from "react-router-dom";

import AdminReportHandling from "../components/AdminReportHandling";
import AdminShopReview from "../components/AdminShopReview";

export default function AdminPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "reports" ? "reports" : "shops";

  function switchTab(value: "shops" | "reports") {
    setSearchParams(value === "shops" ? {} : { tab: "reports" });
  }

  return (
    <main className="page admin-page">
      <h1>管理员工作台</h1>
      <p className="subtitle">审核用户提交的店铺，处理用户对评价的举报。</p>

      <div className="admin-tabs">
        <button
          type="button"
          className={tab === "shops" ? "tab active" : "tab"}
          onClick={() => switchTab("shops")}
        >
          店铺审核
        </button>
        <button
          type="button"
          className={tab === "reports" ? "tab active" : "tab"}
          onClick={() => switchTab("reports")}
        >
          评价举报处理
        </button>
      </div>

      {tab === "shops" ? <AdminShopReview /> : <AdminReportHandling />}
    </main>
  );
}
