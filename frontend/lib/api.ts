import {
    TriageInput,
    TriageOutput,
    PendingTicketsResponse,
    ReviewAction,
    CaseHistoryResponse,
    CaseStatus,
} from "./types";

const API_BASE_URL = "/api";

class ApiError extends Error {
    constructor(
        public status: number,
        message: string
    ) {
        super(message);
        this.name = "ApiError";
    }
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const errorText = await response.text();
        throw new ApiError(
            response.status,
            `API Error: ${response.statusText} - ${errorText}`
        );
    }
    return response.json();
}

export async function triageInvoke(
    input: TriageInput
): Promise<TriageOutput> {
    const response = await fetch(`${API_BASE_URL}/triage/invoke`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(input),
    });

    return handleResponse<TriageOutput>(response);
}

export async function getPendingTickets(): Promise<PendingTicketsResponse> {
    const response = await fetch(`${API_BASE_URL}/admin/review`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    return handleResponse<PendingTicketsResponse>(response);
}

export async function submitReview(
    threadId: string,
    action: ReviewAction
): Promise<TriageOutput> {
    const response = await fetch(
        `${API_BASE_URL}/admin/review?thread_id=${encodeURIComponent(threadId)}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ action }),
        }
    );

    return handleResponse<TriageOutput>(response);
}

export async function getCaseHistory(params?: {
    status?: CaseStatus;
    limit?: number;
    offset?: number;
}): Promise<CaseHistoryResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

    const qs = searchParams.toString();
    const url = `${API_BASE_URL}/cases/history${qs ? `?${qs}` : ""}`;
    
    const response = await fetch(url, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    return handleResponse<CaseHistoryResponse>(response);
}
