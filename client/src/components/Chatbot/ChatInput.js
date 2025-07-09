// --- COMPONENT: ChatInput.js - UPDATED ---
import React, { useRef } from 'react';
import styles from './Chatbot.module.scss';
import classNames from 'classnames/bind';
import { FaPaperPlane, FaMicrophone, FaMicrophoneSlash, FaVolumeUp, FaVolumeMute } from 'react-icons/fa';

const cx = classNames.bind(styles);

const ChatInput = ({
    message,
    setMessage,
    isLoading,
    isTTSEnabled,
    isRecognitionActive,
    showFlowButton,
    currentOptions,
    inStepMode,
    onSend,
    onSendOption,
    onStepControl,
    onStartListening,
    onStopListening,
    onToggleTTS,
}) => {
    const inputRef = useRef(null);

    // BỎ AUTO FOCUS - chỉ focus khi user gửi tin nhắn
    const handleSend = () => {
        onSend();
        // Focus input sau khi gửi tin nhắn để user có thể tiếp tục nhập
        setTimeout(() => {
            if (inputRef.current) {
                inputRef.current.focus();
            }
        }, 100);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleSendOption = async (option) => {
        try {
            await onSendOption(option);
            // Focus input sau khi chọn option
            setTimeout(() => {
                if (inputRef.current) {
                    inputRef.current.focus();
                }
            }, 100);
        } catch (error) {
            console.error('Option send error:', error);
        }
    };

    const handleFlowGuide = async () => {
        try {
            await onSendOption('Hướng dẫn quy trình');
            // Focus input sau khi bấm flow guide
            setTimeout(() => {
                if (inputRef.current) {
                    inputRef.current.focus();
                }
            }, 100);
        } catch (error) {
            console.error('Flow guide error:', error);
        }
    };

    return (
        <div className={cx('input-container')}>
            {/* Flow Button */}
            {showFlowButton && (
                <div className={cx('action-buttons')}>
                    <button className={cx('flow-button')} onClick={handleFlowGuide} disabled={isLoading}>
                        📋 Hướng dẫn quy trình
                    </button>
                </div>
            )}

            {/* Step Controls */}
            {inStepMode && (
                <div className={cx('step-controls')}>
                    <button
                        onClick={() => onStepControl('Quay lại')}
                        disabled={isLoading}
                        className={cx('step-button', 'prev')}
                    >
                        ⬅️ Quay lại
                    </button>
                    <button
                        onClick={() => onStepControl('Tiếp tục')}
                        disabled={isLoading}
                        className={cx('step-button', 'next')}
                    >
                        ➡️ Tiếp tục
                    </button>
                    <button
                        onClick={() => handleSendOption("Kết thúc hướng dẫn")}
                        disabled={isLoading}
                        className={cx('step-button', 'finish')}
                    >
                         Kết thúc hướng dẫn
                    </button>
                </div>
            )}

            {/* Options */}
            {!inStepMode && currentOptions.length > 0 && (
                <div className={cx('options')}>
                    {currentOptions.map((opt, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleSendOption(opt)}
                            className={cx('option-button')}
                            disabled={isLoading}
                        >
                            {opt}
                        </button>
                    ))}
                </div>
            )}

            {/* Input Area - LUÔN HIỂN THỊ */}
            <div className={cx('input-area')}>
                <input
                    type="text"
                    ref={inputRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder={
                        isLoading
                            ? 'Đang xử lý...'
                            : inStepMode
                            ? 'Nhập câu hỏi hoặc sử dụng các nút điều khiển...'
                            : 'Nhập câu hỏi của bạn...'
                    }
                    className={cx('input')}
                    disabled={isLoading}
                />

                {/* TTS Button - Ẩn tạm thời */}
                {false ? (
                    <button
                        onClick={onToggleTTS}
                        className={cx('voice-button', { active: isTTSEnabled })}
                        title={isTTSEnabled ? 'Tắt giọng nói' : 'Bật giọng nói'}
                        disabled={isLoading}
                    >
                        {isTTSEnabled ? <FaVolumeUp /> : <FaVolumeMute />}
                    </button>
                ) : null}

                {/* Voice Input Button */}
                <button
                    onClick={isRecognitionActive ? onStopListening : onStartListening}
                    className={cx('voice-button', {
                        active: isRecognitionActive,
                    })}
                    disabled={isLoading}
                    title={isRecognitionActive ? 'Dừng nghe' : 'Nói để nhập văn bản'}
                >
                    {isRecognitionActive ? <FaMicrophoneSlash /> : <FaMicrophone />}
                </button>

                {/* Send Button - LUÔN HIỂN THỊ */}
                <button
                    onClick={handleSend}
                    className={cx('send-button')}
                    disabled={isLoading || !message.trim()}
                    title={
                        isLoading ? 'Đang gửi...' : !message.trim() ? 'Nhập tin nhắn để gửi' : 'Gửi tin nhắn (Enter)'
                    }
                >
                    <FaPaperPlane />
                </button>
            </div>
        </div>
    );
};

export default ChatInput;