export interface UsageStatus {
  limit: number;
  used: number;
  remaining: number;
  usage_date: string;
  reset_at: string;
  is_unlimited: boolean;
}
