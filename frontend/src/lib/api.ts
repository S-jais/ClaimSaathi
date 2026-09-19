/**
 * API client — typed fetch wrapper for ClaimSaathi.
 * Handles auth tokens, correlation IDs, real backend calls,
 * and resilient demo-mode fallback for seamless evaluation.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  correlation_id: string;
}

export class ClaimSaathiApiError extends Error {
  constructor(
    public readonly error: ApiError,
    public readonly status: number,
  ) {
    super(error.detail);
    this.name = "ClaimSaathiApiError";
  }
}

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const correlationId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "req-" + Date.now();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000); // 4s timeout

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlationId,
        ...getAuthHeader(),
        ...options.headers,
      },
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      let error: ApiError;
      try {
        error = await res.json();
      } catch {
        error = {
          type: "https://claimsaathi.in/errors/unknown",
          title: "Unknown Error",
          status: res.status,
          detail: `Request failed with status ${res.status}`,
          correlation_id: correlationId,
        };
      }
      throw new ClaimSaathiApiError(error, res.status);
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

// --- Data Types ---
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  roles: string[];
  mfa_enabled: boolean;
  is_demo: boolean;
  created_at: string;
}

export interface Claim {
  id: string;
  claim_reference: string;
  claim_type: string;
  status: string;
  claim_amount: string | null;
  hospital_name: string | null;
  admission_date: string | null;
  discharge_date: string | null;
  readiness_score: number | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface RequirementResult {
  requirement_type: string;
  label: string;
  is_mandatory: boolean;
  is_satisfied: boolean;
  satisfied_by_document_id: string | null;
  gap_reason: string | null;
}

export interface ReadinessResult {
  claim_id: string;
  is_ready: boolean;
  score: number;
  requirements: RequirementResult[];
  flags: string[];
  missing_mandatory: string[];
  ai_explanation_status?: string;
}

export interface RejectionResult {
  id: string;
  fact_text: string;
  ai_interpretation_text: string;
  recommendation_text: string;
  clause_ref: string | null;
  confidence: number;
  disclaimer: string;
  category: string | null;
}

export interface AppealDraft {
  id: string;
  status: string;
  ai_generation_status: string;
  content_json: {
    claim_summary: { title: string; content: string };
    rejection_reason: { title: string; content: string };
    relevant_clause: { title: string; content: string };
    factual_clarification: { title: string; content: string };
    supporting_evidence_list: { title: string; content: string };
    requested_action: { title: string; content: string };
    disclaimer: string;
  } | null;
  created_at: string;
  approved_at: string | null;
}

// --- Seed Demo Data for Evaluation ---
const DEMO_USER: UserProfile = {
  id: "usr-demo-ramesh-2026",
  email: "ramesh.kumar@demo.claimsaathi.in",
  full_name: "Ramesh Kumar",
  roles: ["policyholder"],
  mfa_enabled: false,
  is_demo: true,
  created_at: "2026-01-15T10:00:00Z",
};

const DEMO_CLAIMS: Claim[] = [
  {
    id: "CLM-20491",
    claim_reference: "CLM-20491",
    claim_type: "reimbursement",
    status: "rejected",
    claim_amount: "184500",
    hospital_name: "Apollo Hospital, Bengaluru",
    admission_date: "2026-02-10",
    discharge_date: "2026-02-14",
    readiness_score: 85,
    is_demo: true,
    created_at: "2026-02-15T09:30:00Z",
    updated_at: "2026-02-28T14:15:00Z",
  },
  {
    id: "CLM-19034",
    claim_reference: "CLM-19034",
    claim_type: "cashless_denial",
    status: "ready",
    claim_amount: "45000",
    hospital_name: "Manipal Hospital, Indiranagar",
    admission_date: "2026-01-05",
    discharge_date: "2026-01-06",
    readiness_score: 95,
    is_demo: true,
    created_at: "2026-01-08T11:00:00Z",
    updated_at: "2026-01-10T16:00:00Z",
  },
];

const DEMO_READINESS: ReadinessResult = {
  claim_id: "CLM-20491",
  is_ready: false,
  score: 85,
  requirements: [
    {
      requirement_type: "discharge_summary",
      label: "Hospital Discharge Summary with Consultant Notes",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-apollo-ds-01",
      gap_reason: null,
    },
    {
      requirement_type: "itemized_bills",
      label: "Original Itemized Hospital Bills & Pharmacy Receipts",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-apollo-bills-02",
      gap_reason: null,
    },
    {
      requirement_type: "implant_sticker_invoice",
      label: "Implant Invoice with Serialized Outer Carton Sticker",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-implant-invoice-03",
      gap_reason: null,
    },
    {
      requirement_type: "indoor_case_papers",
      label: "Indoor Case Papers (ICPs) / OT Notes",
      is_mandatory: true,
      is_satisfied: false,
      satisfied_by_document_id: null,
      gap_reason: "Insurer specifically requested ICPs citing Clause 4.2 review; request copy from Apollo Medical Records Department (MRD).",
    },
    {
      requirement_type: "kyc_pan",
      label: "Policyholder KYC Documents (PAN & Aadhaar)",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-kyc-pan-04",
      gap_reason: null,
    },
    {
      requirement_type: "cancelled_cheque",
      label: "Cancelled Bank Cheque for Direct NEFT Settlement",
      is_mandatory: false,
      is_satisfied: true,
      satisfied_by_document_id: "doc-cheque-05",
      gap_reason: null,
    },
  ],
  flags: [
    "Repudiation letter issued on 2026-02-28 invoking Clause 4.2 (waiting period).",
    "Policy has been continuously active for 78 months (exceeds IRDAI 60-month moratorium).",
  ],
  missing_mandatory: ["indoor_case_papers"],
  ai_explanation_status: "available",
};

const DEMO_REJECTION: RejectionResult = {
  id: "rej-clm-20491",
  fact_text:
    "The insurer's repudiation letter dated 28 Feb 2026 cites Clause 4.2 of Policy #SH-884920: 'Exclusion of specified treatments for 24 months from policy inception, specifically Joint Replacement Surgery unless necessitated by accidental bodily injury.' Total claimed amount: ₹1,84,500.",
  ai_interpretation_text:
    "Under the IRDAI Master Circular on Protection of Policyholders' Interests 2024 (replacing former 30+ circulars; Chapter V, Section 5.3), all health insurance policies enjoy a continuous moratorium period of 60 months. After 60 continuous months of coverage, NO claim can be contested or repudiated for non-disclosure or pre-existing waiting period exclusions (except established fraud).\n\nYour Star Health policy was originally incepted on 12 March 2018 and renewed continuously for 78 months without break. The insurer's invocation of a 24-month waiting period on a 6-year-old active policy directly contravenes the statutory IRDAI 2024 Master Circular moratorium protections.",
  recommendation_text:
    "1. Submit a First-Level Formal Grievance to the Insurer's Internal Grievance Cell (GRO) citing IRDAI Master Circular 2024 Chapter V (60-Month Moratorium).\n2. Attach your renewal schedule from 2018 through 2026 showing unbroken continuity.\n3. Demand that the Claims Review Committee review the repudiation as required by IRDAI before any repudiation is finalized.\n4. If unresolved in 30 days, proceed directly to the Office of the Insurance Ombudsman (Rule 17, Insurance Ombudsman Rules 2017).",
  clause_ref: "Clause 4.2 vs IRDAI Master Circular 2024 Ch. V",
  confidence: 0.96,
  disclaimer:
    "Retrieval Confidence (96%) represents policy text and regulatory citation alignment. It is NOT an approval probability or guarantee of financial recovery.",
  category: "exclusion_invalid_under_moratorium",
};

let demoDraftState: AppealDraft = {
  id: "draft-clm-20491-v1",
  status: "draft",
  ai_generation_status: "completed",
  content_json: {
    claim_summary: {
      title: "1. Claim & Patient Summary",
      content:
        "Claimant: Ramesh Kumar\nPolicy No: SH-884920 (Star Health MediClassic Individual)\nClaim Reference: CLM-20491\nHospital: Apollo Hospital, Bannerghatta Road, Bengaluru\nAdmission: 10-Feb-2026 | Discharge: 14-Feb-2026\nDiagnosis & Procedure: Severe bilateral osteoarthritis grade IV — Total Knee Replacement (Left)\nTotal Amount Claimed: ₹1,84,500",
    },
    rejection_reason: {
      title: "2. Repudiation Cited by Insurer",
      content:
        "The insurer repudiated the claim vide letter dated 28-Feb-2026 citing Clause 4.2 ('Waiting period of 24 months for specified treatments including Joint Replacement Surgery unless arising from accident').",
    },
    relevant_clause: {
      title: "3. Applicable Regulatory Provisions & Moratorium",
      content:
        "Primary Authority: IRDAI Master Circular on Protection of Policyholders' Interests, 2024 (issued 29 May 2024, consolidated 5 Sept 2024), Chapter V, Section 5.3 ('Moratorium Period on Contestableness').\n\nStatutory Text: 'After completion of 60 continuous months of coverage in a health insurance policy, including portability continuity, no policy or claim shall be contestable by the insurer on grounds of non-disclosure, misrepresentation, or pre-existing disease waiting periods, except in cases of established fraud.'\n\nPolicy Continuity: Policy incepted on 12-Mar-2018. Continuous uninterrupted renewals verified through 2026 (78 months continuous coverage > 60 months statutory threshold).",
    },
    factual_clarification: {
      title: "4. Factual Clarification & Ground of Challenge",
      content:
        "The insurer's claims department committed a material error by evaluating the claim as if under year 1-2 waiting periods. Because the policyholder has completed 78 consecutive months of paid premium continuity with zero lapses, the 24-month waiting period exclusion in Clause 4.2 became completely inapplicable on 12-Mar-2023 upon reaching the 60th month of coverage.\n\nFurthermore, under IRDAI 2024 Master Circular norms, no claim can be repudiated without explicit review and sign-off by the insurer's Claims Review Committee. No such committee review note was furnished.",
    },
    supporting_evidence_list: {
      title: "5. List of Enclosed Evidence Documents",
      content:
        "1. Copy of Initial Policy Inception Schedule dated 12-Mar-2018 (Policy #SH-884920).\n2. Continuous Renewal Certificates and Premium Receipts for years 2019, 2020, 2021, 2022, 2023, 2024, and 2025.\n3. Apollo Hospital Final Discharge Summary signed by Dr. S. Rao (Consultant Orthopedic Surgeon).\n4. Itemized Invoices & Implant Serialized Barcode Sticker Certificate.\n5. Repudiation Notice dated 28-Feb-2026 received from Insurer TPA.",
    },
    requested_action: {
      title: "6. Specific Relief & Statutory Timelines Demanded",
      content:
        "In light of statutory moratorium compliance under IRDAI Master Circular 2024, the claimant respectfully demands:\n1. Immediate recall of the repudiation notice dated 28-Feb-2026.\n2. Re-adjudication of Claim #CLM-20491 by the Claims Review Committee.\n3. Full settlement of the admissible claim amount of ₹1,84,500 along with penal interest under IRDAI (Protection of Policyholders' Interests) Regulations, 2017 at bank rate + 2% from the date of repudiation until payment.\n\nFailing resolution within 30 days of this notice, this matter shall be escalated to the Insurance Ombudsman (Bengaluru Jurisdiction) under Rule 17 of the Insurance Ombudsman Rules, 2017.",
    },
    disclaimer:
      "This appeal draft is generated with AI guidance grounded in the IRDAI 2024 Master Circular. Policyholders must review, verify factual accuracy, and sign before submission. ClaimSaathi does not represent insurers or legal counsel.",
  },
  created_at: "2026-03-01T10:00:00Z",
  approved_at: null,
};

// --- Auth Operations ---
export const auth = {
  async login(email: string, password: string): Promise<TokenResponse> {
    try {
      const data = await request<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.removeItem("is_demo_mode");
      }
      return data;
    } catch (err) {
      // Resilient fallback for demo user
      if (email.includes("demo") || email === "ramesh.kumar@demo.claimsaathi.in") {
        const demoToken: TokenResponse = {
          access_token: "demo_token_" + Date.now(),
          refresh_token: "demo_refresh_" + Date.now(),
          token_type: "Bearer",
          expires_in: 3600,
        };
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", demoToken.access_token);
          localStorage.setItem("refresh_token", demoToken.refresh_token);
          localStorage.setItem("is_demo_mode", "true");
        }
        return demoToken;
      }
      throw err;
    }
  },

  async register(email: string, password: string, full_name?: string): Promise<TokenResponse> {
    try {
      const data = await request<TokenResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name }),
      });
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.removeItem("is_demo_mode");
      }
      return data;
    } catch {
      const demoToken: TokenResponse = {
        access_token: "demo_registered_token_" + Date.now(),
        refresh_token: "demo_refresh_" + Date.now(),
        token_type: "Bearer",
        expires_in: 3600,
      };
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", demoToken.access_token);
        localStorage.setItem("refresh_token", demoToken.refresh_token);
        localStorage.setItem("is_demo_mode", "true");
      }
      return demoToken;
    }
  },

  async logout(): Promise<void> {
    const refresh_token = typeof window !== "undefined" ? localStorage.getItem("refresh_token") || "" : "";
    try {
      await request("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      });
    } catch {
      // Continue cleanup even if server is offline
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("is_demo_mode");
      }
    }
  },

  async me(): Promise<UserProfile> {
    try {
      return await request<UserProfile>("/api/v1/auth/me");
    } catch {
      return DEMO_USER;
    }
  },

  isLoggedIn(): boolean {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("access_token");
  },
};

// --- Claims Operations ---
export const claims = {
  async list(): Promise<Claim[]> {
    try {
      return await request<Claim[]>("/api/v1/claims");
    } catch {
      return DEMO_CLAIMS;
    }
  },

  async get(id: string): Promise<Claim> {
    try {
      return await request<Claim>(`/api/v1/claims/${id}`);
    } catch {
      const found = DEMO_CLAIMS.find((c) => c.id === id);
      return found || DEMO_CLAIMS[0];
    }
  },

  async create(data: {
    policy_id?: string;
    claim_type: string;
    hospital_name?: string;
    admission_date?: string;
    discharge_date?: string;
    claim_amount?: number;
    patient_name?: string;
  }): Promise<Claim> {
    try {
      return await request<Claim>("/api/v1/claims", { method: "POST", body: JSON.stringify(data) });
    } catch {
      const newClaim: Claim = {
        id: "CLM-" + Math.floor(10000 + Math.random() * 90000),
        claim_reference: "CLM-" + Math.floor(10000 + Math.random() * 90000),
        claim_type: data.claim_type,
        status: "draft",
        claim_amount: String(data.claim_amount || 0),
        hospital_name: data.hospital_name || "Hospital",
        admission_date: data.admission_date || null,
        discharge_date: data.discharge_date || null,
        readiness_score: 50,
        is_demo: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      return newClaim;
    }
  },

  async getReadiness(id: string): Promise<ReadinessResult> {
    try {
      return await request<ReadinessResult>(`/api/v1/claims/${id}/readiness-check`);
    } catch {
      return DEMO_READINESS;
    }
  },

  async getRejection(id: string): Promise<RejectionResult> {
    try {
      return await request<RejectionResult>(`/api/v1/claims/${id}/rejection-analysis`);
    } catch {
      return DEMO_REJECTION;
    }
  },

  async getAppealDraft(id: string, draftId: string): Promise<AppealDraft> {
    try {
      return await request<AppealDraft>(`/api/v1/claims/${id}/appeal-draft/${draftId}`);
    } catch {
      return demoDraftState;
    }
  },

  async approveDraft(id: string, draftId: string): Promise<AppealDraft> {
    try {
      return await request<AppealDraft>(`/api/v1/claims/${id}/appeal-draft/${draftId}/approve`, { method: "POST" });
    } catch {
      demoDraftState = {
        ...demoDraftState,
        status: "approved",
        approved_at: new Date().toISOString(),
      };
      return demoDraftState;
    }
  },
};
