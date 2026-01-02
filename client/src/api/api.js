// api.js - Fixed version for Chat System
import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_URL = 'http://localhost:5000/api';

// Tạo axios instance với cấu hình mặc định
const apiClient = axios.create({
    baseURL: BASE_URL,
    timeout: 30000, // 30 seconds timeout
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor để xử lý lỗi chung
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// ------------------------- CHAT API -------------------------

export const sendMessageToBot = async (message, userId, domain = "xuatnhapcanh") => {
    try {
        const response = await apiClient.post('/chat/ask', {
            message,
            user_id: userId,
            domain: domain
        });
        return response.data;
    } catch (error) {
        console.error('❌ Lỗi gửi tin nhắn:', error);
        throw error;
    }
};

// ----------------------- STATIC FILE HELPERS -----------------------

export const getStaticFileUrl = (filePath) => {
    if (!filePath) return null;
    
    // Nếu đã là URL đầy đủ thì return luôn
    if (filePath.startsWith('http')) {
        return filePath;
    }
    
    // Nếu là relative path từ dataset/
    if (filePath.startsWith('dataset/')) {
        return `${BASE_URL}/static/${filePath}`;
    }
    
    // Fallback
    return `${BASE_URL}/static/data/${filePath}`;
};

export const getImageUrl = (imagePath) => {
    return getStaticFileUrl(imagePath);
};

// ----------------------- HEALTH CHECK -----------------------

export const checkServerHealth = async () => {
    try {
        const response = await apiClient.get('/');
        return response.data;
    } catch (error) {
        console.error('❌ Lỗi kiểm tra server:', error);
        throw error;
    }
};

// ---------------------- UTILITY FUNCTIONS ----------------

export const handleApiError = (error) => {
    if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        const message = error.response.data?.error || 
                       error.response.data?.message || 
                       error.response.data?.text || 
                       'Lỗi không xác định';
        
        switch (status) {
            case 400:
                return `Dữ liệu không hợp lệ: ${message}`;
            case 403:
                return `Truy cập bị từ chối: ${message}`;
            case 404:
                return 'Endpoint không tồn tại';
            case 500:
                return `Lỗi server: ${message}`;
            default:
                return `Lỗi ${status}: ${message}`;
        }
    } else if (error.request) {
        // Network error
        return 'Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng.';
    } else {
        // Other error
        return `Lỗi: ${error.message}`;
    }
};

// ---------------------- RESPONSE HELPERS ----------------

export const isFlowResponse = (response) => {
    return response?.type === 'step' || 
           response?.step_mode === true ||
           response?.type === 'question';
};

export const isFlowCompleted = (response) => {
    return response?.type === 'completed' || 
           response?.flow_completed === true;
};

export const hasGuideImage = (response) => {
    return Boolean(response?.guide_image);
};

export const hasExternalLink = (response) => {
    return Boolean(response?.external_link);
};

export const hasTTSText = (response) => {
    return Boolean(response?.tts_text);
};

export const getFlowProgress = (response) => {
    if (response?.progress_percent) {
        return response.progress_percent;
    }
    
    if (response?.current_step && response?.total_steps) {
        return Math.round((response.current_step / response.total_steps) * 100);
    }
    
    return 0;
};

export const getFlowNavigation = (response) => {
    return response?.navigation || {
        can_go_back: false,
        can_go_forward: false,
        is_first_step: true,
        is_last_step: true
    };
};

// Test connection
export const testConnection = async () => {
    try {
        const response = await checkServerHealth();
        return {
            success: true,
            message: 'Kết nối thành công',
            data: response
        };
    } catch (error) {
        return {
            success: false,
            message: handleApiError(error),
            error: error
        };
    }
};

// ---------------------- DEBUG HELPERS ----------------

export const logResponseStructure = (response) => {
    console.group('🔍 Response Structure');
    console.log('Type:', response?.type);
    console.log('Source:', response?.source);
    console.log('Step Mode:', response?.step_mode);
    console.log('Buttons:', response?.buttons);
    console.log('Guide Image:', response?.guide_image);
    console.log('External Link:', response?.external_link);
    console.log('Progress:', getFlowProgress(response) + '%');
    console.log('Navigation:', getFlowNavigation(response));
    console.log('Full Response:', response);
    console.groupEnd();
};

// Default export với object
const apiHelpers = {
    sendMessageToBot,
    getStaticFileUrl,
    getImageUrl,
    checkServerHealth,
    handleApiError,
    isFlowResponse,
    isFlowCompleted,
    hasGuideImage,
    hasExternalLink,
    hasTTSText,
    getFlowProgress,
    getFlowNavigation,
    testConnection,
    logResponseStructure
};

export default apiHelpers;


// -----------------Auth----------------------
