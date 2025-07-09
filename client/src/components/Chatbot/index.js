// --- COMPONENT CHA: index.js (UPDATED) ---
import React from 'react';
import styles from './Chatbot.module.scss';
import classNames from 'classnames/bind';
import { useChatbot } from './useChatbot';
import ChatWindow from './ChatWindow';
import ChatInput from './ChatInput';

const cx = classNames.bind(styles);

const Chatbot = ({ userId = 'anonymous', className, onDataUpdate, ...props }) => {
    // Sử dụng custom hook để quản lý logic
    const {
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

        // State mới cho guide
        currentStep,
        flowData,
        guideImage,
        guideInfo,

        // Methods
        handleSend,
        handleSendOption,
        handleStepControl,
        startListening,
        stopListening,
        toggleTTS,
    } = useChatbot(userId, onDataUpdate); // TRUYỀN CALLBACK VÀO HOOK

    return (
        <div className={cx('chatbot-wrapper', className)} {...props}>
            {/* Chat Display Area */}
            <div className={cx('chat-body')}>
                <ChatWindow
                    responses={responses}
                    isLoading={isLoading}
                    isListening={isListening}
                    sessionInfo={sessionInfo}
                    connectionStatus={connectionStatus}
                />
            </div>

            {/* Input Area */}
            <div className={cx('input-separator')}>
                <ChatInput
                    message={message}
                    setMessage={setMessage}
                    isLoading={isLoading}
                    // isTTSEnabled={isTTSEnabled}
                    isRecognitionActive={isRecognitionActive}
                    showFlowButton={showFlowButton}
                    currentOptions={currentOptions}
                    inStepMode={inStepMode}
                    onSend={handleSend}
                    onSendOption={handleSendOption}
                    onStepControl={handleStepControl}
                    onStartListening={startListening}
                    onStopListening={stopListening}
                    onToggleTTS={toggleTTS}
                />
            </div>
        </div>
    );
};

export default Chatbot;