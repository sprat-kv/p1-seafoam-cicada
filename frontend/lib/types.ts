// Type definitions based on OpenAPI schema

export type ReviewStatus = "pending" | "approved" | "rejected";

export type DraftScenario =
  | "reply"
  | "need_identifier"
  | "order_not_found"
  | "no_orders_found"
  | "confirm_order";

export interface TriageInput {
  ticket_text: string;
  order_id?: string | null;
  thread_id?: string | null;
}

export interface TriageOutput {
  thread_id: string;
  order_id?: string | null;
  email?: string | null;
  issue_type?: string | null;
  draft_scenario?: DraftScenario | null;
  draft_reply?: string | null;
  suggested_action?: string | null;
  review_status?: ReviewStatus | null;
  evidence?: string | null;
  recommendation?: string | null;
  candidate_orders?: any[] | null;
  messages?: any[];
  order?: any | null;
  reply_text?: string | null;
}

export interface PendingTicket {
  thread_id: string;
  order_id?: string | null;
  customer_name?: string | null;
  issue_type?: string | null;
  suggested_action?: string | null;
  applied_policies?: AppliedPolicy[] | null;
  draft_reply?: string | null;
  created_at?: string | null;
}

export interface AppliedPolicy {
  source: string;
  title: string;
  cited_rule: string;
  compliance: "compliant" | "non_compliant" | "requires_review";
}

export interface PendingTicketsResponse {
  pending_count: number;
  tickets: PendingTicket[];
}

export interface ReviewAction {
  status: ReviewStatus;
  feedback?: string | null;
}

export interface AdminReviewInput {
  action: ReviewAction;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
}
