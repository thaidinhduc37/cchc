import React, { useEffect, useRef, useState } from 'react';
import styles from './Chatbot.module.scss';
import classNames from 'classnames/bind';
import images from '~/assets/images';

const cx = classNames.bind(styles);

const parseMarkdown = (text) => {
    if (!text) return text;

    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');

    const urlRegex = /(https?:\/\/[^\s<>"]+|www\.[^\s<>"]+|ftp:\/\/[^\s<>"]+)/gi;
    text = text.replace(urlRegex, (url) => {
        let href = url.startsWith('www.') ? 'https://' + url : url;
        return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="${cx('chat-link')}" onclick="event.stopPropagation(); return true;">${url}</a>`;
    });

    return text.replace(/\n/g, '<br/>');
};

const TypingMessage = ({ text, onComplete }) => {
    const [displayedText, setDisplayedText] = useState('');
    const [isTyping, setIsTyping] = useState(true);
    const indexRef = useRef(0);

    useEffect(() => {
        if (!text || text.length === 0) {
            setIsTyping(false);
            onComplete && onComplete();
            return;
        }

        const typeSpeed = 30;

        const typeText = () => {
            if (indexRef.current < text.length) {
                setDisplayedText(text.slice(0, indexRef.current + 1));
                indexRef.current += 1;
                setTimeout(typeText, typeSpeed);
            } else {
                setIsTyping(false);
                onComplete && onComplete();
            }
        };

        indexRef.current = 0;
        setDisplayedText('');
        setIsTyping(true);

        setTimeout(typeText, 100);

        return () => {
            indexRef.current = text.length;
            setDisplayedText(text);
            setIsTyping(false);
        };
    }, [text, onComplete]);

    return (
        <div className={cx('typing-message-content')}>
            <div
                dangerouslySetInnerHTML={{
                    __html: parseMarkdown(displayedText),
                }}
            />
            {isTyping && <span className={cx('typing-cursor')}>|</span>}
        </div>
    );
};

const ChatWindow = ({ responses, isLoading, isListening, sessionInfo, connectionStatus }) => {
    const chatWindowRef = useRef(null);
    const chatEndRef = useRef(null);
    const [completedMessages, setCompletedMessages] = useState(new Set());
    const [isLinkClicked, setIsLinkClicked] = useState(false);

    useEffect(() => {
        const scrollContainer = chatWindowRef.current;
        if (!scrollContainer) return;

        const isNearBottom = () => {
            const threshold = 100;
            return (
                scrollContainer.scrollHeight - scrollContainer.scrollTop <=
                scrollContainer.clientHeight + threshold
            );
        };

        // Cuộn xuống khi có tin nhắn mới hoặc gần dưới cùng
        if (responses.length > 0 && !isLinkClicked && isNearBottom()) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }

        const handleScroll = () => {
            if (!isLinkClicked && isNearBottom()) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        };

        scrollContainer.addEventListener('scroll', handleScroll);
        return () => scrollContainer.removeEventListener('scroll', handleScroll);
    }, [responses, isLoading, isLinkClicked]);

    const handleTypingComplete = (messageIndex) => {
        setCompletedMessages((prev) => new Set([...prev, messageIndex]));
    };

    const handleLinkClick = () => {
        setIsLinkClicked(true);
        setTimeout(() => setIsLinkClicked(false), 1500); // Tăng delay để ổn định giao diện
    };

    return (
        <div className={cx('chat-container')}>
            {sessionInfo && sessionInfo.exists && (
                <div className={cx('session-info')}>
                    <small>
                        Phiên: {sessionInfo.conversation_count} tin nhắn • Thời gian:{' '}
                        {Math.round(sessionInfo.duration / 60)}p
                    </small>
                </div>
            )}

            <div className={cx('chat-window')} ref={chatWindowRef}>
                {responses.map((res, index) => (
                    <div key={index} className={cx('message', res.sender)}>
                        <img
                            src={res.sender === 'bot' ? images.logo : images.userAvatar}
                            alt="avatar"
                            className={cx('message-avatar')}
                        />
                        <div className={cx('message-content')} onClick={handleLinkClick}>
                            {res.sender === 'bot' && !completedMessages.has(index) ? (
                                <TypingMessage text={res.text} onComplete={() => handleTypingComplete(index)} />
                            ) : (
                                <div
                                    dangerouslySetInnerHTML={{
                                        __html: parseMarkdown(res.text),
                                    }}
                                />
                            )}
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