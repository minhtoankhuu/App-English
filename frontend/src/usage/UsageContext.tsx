import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from "react";
import { getMyUsage } from "../api/usage";
import type { UserOut } from "../types/auth";
import type { UsageStatus } from "../types/usage";

interface UsageContextValue {
  status: UsageStatus | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const UsageContext = createContext<UsageContextValue | null>(null);

export function UsageProvider({ user, children }: PropsWithChildren<{ user: UserOut }>) {
  const [status, setStatus] = useState<UsageStatus | null>(null);
  const [loading, setLoading] = useState(user.role === "teacher");

  const refresh = useCallback(async () => {
    if (user.role === "admin") return;
    setLoading(true);
    try {
      setStatus(await getMyUsage());
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, [user.role]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(() => ({ status, loading, refresh }), [status, loading, refresh]);
  return <UsageContext.Provider value={value}>{children}</UsageContext.Provider>;
}

// oxlint-disable-next-line react/only-export-components -- hook và provider dùng chung context riêng tư.
export function useUsage(): UsageContextValue {
  const value = useContext(UsageContext);
  if (!value) throw new Error("useUsage must be used within UsageProvider");
  return value;
}
