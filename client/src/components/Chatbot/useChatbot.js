// --- CUSTOM HOOK: useChatbot.js - ENHANCED FOR TYPING ANIMATION ---
import { useState, useEffect, useRef, useCallback } from 'react';
import { sendMessageToBot, handleApiError, testConnection } from '~/api/api';

export const useChatbot = (userId = 'anonymous', onDataUpdate = null) => {
    // State management
    const [message, setMessage] = useState('');
    const [responses, setResponses] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isTTSEnabled, setIsTTSEnabled] = useState(false);
    const [isRecognitionActive, setIsRecognitionActive] = useState(false);
    const [showFlowButton, setShowFlowButton] = useState(false);
    const [currentOptions, setCurrentOptions] = useState([]);
    const [inStepMode, setInStepMode] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState('unknown');
    const [isListening, setIsListening] = useState(false);
    const [sessionInfo, setSessionInfo] = useState(null);

    // STATE MỚI CHO GUIDE DATA
    const [currentStep, setCurrentStep] = useState(null);
    const [flowData, setFlowData] = useState(null);
    const [guideImage, setGuideImage] = useState(null);
    const [guideInfo, setGuideInfo] = useState(null);

    // STATE MỚI CHO TYPING ANIMATION
    const [isTyping, setIsTyping] = useState(false);

    // Refs
    const recognitionRef = useRef(null);

    // Connection methods - use useCallback to fix dependency warning
    const checkConnection = useCallback(async () => {
        try {
            const result = await testConnection();
            setConnectionStatus(result.success ? 'connected' : 'disconnected');
            if (!result.success) {
                addBotMessage(`⚠️ ${result.message}`);
            }
        } catch (error) {
            setConnectionStatus('disconnected');
            addBotMessage('❌ Không thể kết nối đến server');
        }
    }, []); // No dependencies needed

    // Initialize connection check
    useEffect(() => {
        checkConnection();
    }, [checkConnection]);

    // Cleanup
    useEffect(() => {
        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.abort();
            }
        };
    }, []);

    // Message management - Enhanced cho typing animation
    const addBotMessage = (text) => {
        setResponses((prev) => [...prev, { text, sender: 'bot', timestamp: new Date() }]);
        setIsTyping(false); // Reset typing state khi có tin nhắn mới
    };

    const addUserMessage = (text) => {
        setResponses((prev) => [...prev, { text, sender: 'user', timestamp: new Date() }]);
    };

    // XỬ LÝ DỮ LIỆU TỪ BACKEND VÀ TRUYỀN LÊN RIGHTPANEL
    const handleBackendResponse = (res) => {
        console.log('📄 Processing backend response:', res);

        // Cập nhật các state hiện có
        setShowFlowButton(!!res.show_flow_button);
        setCurrentOptions(res.options || []);
        setInStepMode(!!res.step_mode);

        // XỬ LÝ DỮ LIỆU GUIDE - SỬ DỤNG ĐÚNG FIELD NAMES
        const guideData = {};

        // CURRENT STEP - từ response trực tiếp
        if (res.current_step) {
            setCurrentStep(res.current_step);
            guideData.currentStep = res.current_step;
        }

        // FLOW DATA - tạo từ response data có sẵn
        if (res.flow_id) {
            const flowData = {
                name: res.reply.split('**')[1] || 'Hướng dẫn', // Extract từ reply
                steps: res.total_steps || 1,
                flow_id: res.flow_id,
            };
            setFlowData(flowData);
            guideData.flowData = flowData;
        }

        // GUIDE IMAGE - từ guide_image field
        if (res.guide_image) {
            setGuideImage(res.guide_image);
            guideData.guideImage = res.guide_image;
        }

        // STEP INFO - từ step_info field
        if (res.step_info) {
            setGuideInfo(res.step_info);
            guideData.guideInfo = res.step_info;
        }

        // DETECT FLOW STATE
        const isInFlow = res.type === 'step' || res.step_mode || res.type === 'question';
        guideData.isInFlow = isInFlow;

        console.log('🔍 Extracted guide data:', guideData); // DEBUG

        // TRUYỀN DỮ LIỆU LÊN RIGHTPANEL
        if (onDataUpdate) {
            console.log('📤 Sending data to RightPanel:', guideData);
            onDataUpdate(guideData);
        }
    };

    // TTS simulation (giữ lại cho text-to-speech)
    const speak = (text, onEnd = null) => {
        // Không làm gì - để backend TTS xử lý
        console.log('🔇 Frontend TTS disabled - Backend sẽ xử lý');
        return;
    };

    // Speech Recognition (giữ lại cho speech-to-text)
    const startListening = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            addBotMessage('❌ Trình duyệt không hỗ trợ nhận diện giọng nói');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'vi-VN';
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            setIsRecognitionActive(true);
            setIsListening(true);
            console.log('🎤 Bắt đầu nghe...');
        };

        recognition.onresult = async (event) => {
            const speechResult = event.results[0][0].transcript;
            console.log('🗣️ Nhận diện:', speechResult);

            // Tự động điền vào input và gửi
            setMessage(speechResult);
            setTimeout(() => handleSend(speechResult), 300);
        };

        recognition.onerror = (event) => {
            console.error('STT error:', event.error);
            setIsRecognitionActive(false);
            setIsListening(false);

            switch (event.error) {
                case 'no-speech':
                    addBotMessage('🔇 Không nhận được giọng nói. Vui lòng thử lại.');
                    break;
                case 'network':
                    addBotMessage('🌐 Lỗi mạng. Vui lòng kiểm tra kết nối.');
                    break;
                default:
                    addBotMessage(`❌ Lỗi nhận diện giọng nói: ${event.error}`);
            }
        };

        recognition.onend = () => {
            setIsRecognitionActive(false);
            setIsListening(false);
            console.log('🛑 Dừng nghe');
        };

        recognitionRef.current = recognition;
        recognition.start();
    };

    const stopListening = () => {
        if (recognitionRef.current) {
            recognitionRef.current.abort();
        }
        setIsRecognitionActive(false);
        setIsListening(false);
    };

    // Toggle TTS
    const toggleTTS = () => {
        const newState = !isTTSEnabled;
        setIsTTSEnabled(newState);

        const message = newState ? '🔊 Đã bật đọc tin nhắn' : '🔇 Đã tắt đọc tin nhắn';
        addBotMessage(message);

        if (newState) {
            speak(message);
        }
    };

    // Message sending - Enhanced với typing animation
    const handleSend = async (speechText = null) => {
        const textToSend = speechText || message.trim();

        if (!textToSend || isLoading) return;

        addUserMessage(textToSend);
        setMessage('');
        setIsLoading(true);
        setIsTyping(true); // Bắt đầu typing state

        try {
            const res = await sendMessageToBot(textToSend, userId);
            
            // Delay nhỏ để có hiệu ứng tự nhiên hơn
            setTimeout(() => {
                addBotMessage(res.reply);
                
                // XỬ LÝ DỮ LIỆU TỪ BACKEND
                handleBackendResponse(res);

                // Đọc phản hồi nếu TTS bật
                if (isTTSEnabled && res.reply) {
                    speak(res.reply);
                }
            }, 500);

        } catch (error) {
            const errorMessage = handleApiError(error);
            setTimeout(() => {
                addBotMessage(`❌ ${errorMessage}`);
                setIsTyping(false);
            }, 300);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSendOption = async (option) => {
        addUserMessage(option);
        setIsLoading(true);
        setIsTyping(true);

        try {
            const res = await sendMessageToBot(option, userId);
            
            setTimeout(() => {
                addBotMessage(res.reply);
                
                // XỬ LÝ DỮ LIỆU TỪ BACKEND
                handleBackendResponse(res);

                // Đọc phản hồi nếu TTS bật
                if (isTTSEnabled && res.reply) {
                    speak(res.reply);
                }
            }, 500);

        } catch (error) {
            const errorMessage = handleApiError(error);
            setTimeout(() => {
                addBotMessage(`❌ ${errorMessage}`);
                setIsTyping(false);
            }, 300);
        } finally {
            setIsLoading(false);
        }
    };

    const handleStepControl = async (direction) => {
        setIsLoading(true);
        setIsTyping(true);
        
        try {
            const res = await sendMessageToBot(direction, userId);
            
            setTimeout(() => {
                addBotMessage(res.reply);
                
                // XỬ LÝ DỮ LIỆU TỪ BACKEND
                handleBackendResponse(res);

                // Đọc phản hồi nếu TTS bật
                if (isTTSEnabled && res.reply) {
                    speak(res.reply);
                }

                setInStepMode(!!res.step_mode);
            }, 500);

        } catch (error) {
            const errorMessage = handleApiError(error);
            setTimeout(() => {
                addBotMessage(`❌ ${errorMessage}`);
                setIsTyping(false);
            }, 300);
        } finally {
            setIsLoading(false);
        }
    };

    return {
        // State hiện có
        message,
        setMessage,
        responses,
        isLoading,
        isTTSEnabled,
        isRecognitionActive,
        showFlowButton,
        currentOptions,
        inStepMode,
        connectionStatus,
        isListening,
        sessionInfo,

        // STATE MỚI CHO GUIDE
        currentStep,
        flowData,
        guideImage,
        guideInfo,

        // STATE MỚI CHO TYPING ANIMATION  
        isTyping,

        // Methods
        handleSend,
        handleSendOption,
        handleStepControl,
        startListening,
        stopListening,
        toggleTTS,
        checkConnection,
        addBotMessage,
        addUserMessage,
    };
};