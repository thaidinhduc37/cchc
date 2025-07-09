// --- COMPONENT: ChatWindow.js ---
import React, { useEffect, useRef } from 'react';
import styles from './Chatbot.module.scss';
import classNames from 'classnames/bind';
import images from '~/assets/images';

const cx = classNames.bind(styles);

// Thêm hàm này sau dòng: const cx = classNames.bind(styles);

// Hàm parse markdown đơn giản
// Hàm parse markdown đơn giản
const parseMarkdown = (text) => {
    if (!text) return text;
    
    // Xử lý **bold**
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Xử lý *italic*
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Xử lý `code`
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');

    
    return text;
};

const ChatWindow = ({ responses, isLoading, isListening, sessionInfo, connectionStatus }) => {
    const chatWindowRef = useRef(null);
    const chatEndRef = useRef(null);

    // Auto scroll to bottom khi có tin nhắn mới
    useEffect(() => {
        if (chatWindowRef.current) {
            chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
        }
    }, [responses, isLoading]);

    return (
        <div className={cx('chat-container')}>
            {/* Session Info */}
            {sessionInfo && sessionInfo.exists && (
                <div className={cx('session-info')}>
                    <small>
                        Phiên: {sessionInfo.conversation_count} tin nhắn • Thời gian:{' '}
                        {Math.round(sessionInfo.duration / 60)}p
                    </small>
                </div>
            )}

            {/* Chat Messages */}
            <div className={cx('chat-window')} ref={chatWindowRef}>
                {responses.map((res, index) => (
                    <div key={index} className={cx('message', res.sender)}>
                        <img
                            src={res.sender === 'bot' ? images.logo : images.userAvatar}
                            alt="avatar"
                            className={cx('message-avatar')}
                        />
                        <div className={cx('message-content')}>
                            <div
                                dangerouslySetInnerHTML={{
                                    __html: parseMarkdown(res.text).replace(/\n/g, '<br/>'),
                                }}
                            />
                            {res.timestamp && (
                                <small className={cx('timestamp')}>
                                    {res.timestamp.toLocaleTimeString('vi-VN', {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                    })}
                                </small>
                            )}
                        </div>
                    </div>
                ))}

                {/* Loading Indicator */}
                {isLoading && (
                    <div className={cx('loading')}>
                        <div className={cx('typing-indicator')}>
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        Đang xử lý...
                    </div>
                )}

                {/* Listening Indicator */}
                {isListening && (
                    <div className={cx('message', 'system')}>
                        <div className={cx('message-content')}>
                            <span>🎤 Trợ lý đang lắng nghe...</span>
                        </div>
                    </div>
                )}

                <div ref={chatEndRef} />
            </div>
        </div>
    );
};

export default ChatWindow;
