export type UserRole = 'Admin' | 'Analyst' | 'Reviewer' | 'Viewer';

export interface UserProfile {
  id: number;
  username: string;
  full_name: string | null;
  email: string | null;
  role: UserRole;
  subsidiary: string | null;
  created_at?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface SignupPayload {
  username: string;
  password: string;
  full_name?: string;
  email?: string;
  subsidiary?: string;
}

