import axios from 'axios';

const getBaseURL = () => {
  const envUrl = import.meta.env.VITE_PUBLIC_BACKEND_URL;
  if (!envUrl) return '/api';
  return envUrl.endsWith('/api') ? envUrl : `${envUrl.replace(/\/$/, '')}/api`;
};

const api = axios.create({
  baseURL: getBaseURL(),
});

// --- Types ---

export interface Contract {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  overall_risk_score: number | null;
  risk_level: string | null;
  risk_breakdown: RiskBreakdown | null;
  created_at: string;
  updated_at: string;
}

export interface RiskBreakdown {
  financial: number;
  operational: number;
  legal: number;
  reputational: number;
}

export interface Clause {
  id: string;
  contract_id: string;
  clause_type: string;
  section_number: string | null;
  title: string | null;
  original_text: string;
  plain_english_summary: string | null;
  risk_score: number | null;
  risk_level: string | null;
  risk_category: string | null;
  market_deviation: string | null;
  deviation_explanation: string | null;
}

export interface ContractDetail extends Contract {
  executive_summary: string | null;
  clauses: Clause[];
}

export interface AnalysisStatus {
  contract_id: string;
  status: string;
  progress: number;
  message: string;
}

export interface CompareResult {
  clause_type: string;
  comparisons: Array<{
    contract_id: string;
    contract_name: string;
    clause_text: string;
    risk_score: number | null;
    deviation: string | null;
  }>;
  ai_summary: string | null;
  key_differences: Array<any> | null;
  most_favorable: string | null;
  most_risky: string | null;
  recommendation: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    clause_id: string;
    section_number: string;
    snippet: string;
  }>;
}

// --- Contract endpoints ---

export const uploadContract = async (file: File): Promise<Contract> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/contracts/upload', formData);
  return data;
};

export const getContracts = async (): Promise<Contract[]> => {
  const { data } = await api.get('/contracts');
  return data.contracts;
};

export const getContract = async (id: string): Promise<ContractDetail> => {
  const { data } = await api.get(`/contracts/${id}`);
  return data;
};

export const deleteContract = async (id: string): Promise<void> => {
  await api.delete(`/contracts/${id}`);
};

// --- Analysis endpoints ---

export const triggerAnalysis = async (id: string): Promise<AnalysisStatus> => {
  const { data } = await api.post(`/contracts/${id}/analyze`);
  return data;
};

export const getAnalysisStatus = async (id: string): Promise<AnalysisStatus> => {
  const { data } = await api.get(`/contracts/${id}/status`);
  return data;
};

export const getContractClauses = async (id: string): Promise<Clause[]> => {
  const { data } = await api.get(`/contracts/${id}/clauses`);
  return data;
};

export const getContractSummary = async (id: string): Promise<{ summary: string }> => {
  const { data } = await api.get(`/contracts/${id}/summary`);
  return data;
};

// --- Compare endpoints ---

export const compareContracts = async (
  contractIds: string[],
  clauseType: string,
): Promise<CompareResult> => {
  const { data } = await api.post('/compare', {
    contract_ids: contractIds,
    clause_type: clauseType,
  });
  return data;
};

// --- Chat endpoints ---

export const chatWithContract = async (
  id: string,
  message: string,
): Promise<{ response: string; citations: any[] }> => {
  const { data } = await api.post(`/contracts/${id}/chat`, { message });
  return data;
};

export default api;
