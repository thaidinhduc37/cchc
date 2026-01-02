import axios from 'axios';
const API_URL = 'http://localhost:5000/api';

class AuthService {
    async register(userData) {
        try {
            const response = await axios.post(`${API_URL}/auth/register`, userData);
            if (response.data.access_token) {
                this.setUserData(response.data);
            }
            return response.data;
        } catch (error) {
            throw error.response?.data?.error || 'Đăng ký thất bại';
        }
    }

    async login(credentials) {
        try {
            const response = await axios.post(`${API_URL}/auth/login`, credentials);
            if (response.data.access_token) {
                this.setUserData(response.data);
            }
            return response.data;
        } catch (error) {
            throw error.response?.data?.error || 'Đăng nhập thất bại';
        }
    }

    logout() {
        localStorage.removeItem('user');
        localStorage.removeItem('access_token');
    }

    getCurrentUser() {
        return JSON.parse(localStorage.getItem('user'));
    }

    getToken() {
        return localStorage.getItem('access_token');
    }

    setUserData(data) {
        localStorage.setItem('user', JSON.stringify(data.user));
        localStorage.setItem('access_token', data.access_token);
    }

    isAuthenticated() {
        return !!this.getToken();
    }
}

export default new AuthService();
