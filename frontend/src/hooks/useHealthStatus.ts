import { useEffect, useState } from "react";

import { fetchHealth } from "../api/client";
import type { HealthState } from "../types/api";

export function useHealthStatus(): HealthState {
  const [health, setHealth] = useState<HealthState>({
    phase: "loading",
    message: "正在请求后端健康检查接口……",
  });

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((result) => {
        if (!cancelled) {
          setHealth({ phase: "ok", message: result.message });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setHealth({
            phase: "error",
            message: error instanceof Error ? error.message : "无法连接后端服务",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return health;
}
