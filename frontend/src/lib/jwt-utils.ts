/**
 * JWT token storage and retrieval utilities
 */

const TOKEN_KEY = 'jwt_token';

export const jwtUtils = {
  getToken: (): string | null => {
    const token = localStorage.getItem(TOKEN_KEY);
    return token;
  },

  setToken: (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
  },

  removeToken: (): void => {
    localStorage.removeItem(TOKEN_KEY);
  },

  hasToken: (): boolean => {
    return !!localStorage.getItem(TOKEN_KEY);
  }
};

