import React, { useState, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './NotebookLm.module.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
    faMinus, 
    faPlus, 
    faRotateRight,
    faCircle,
    faExternalLinkAlt,
    faRobot
} from '@fortawesome/free-solid-svg-icons';

const cx = classNames.bind(styles);

const NotebookLm = () => {
    const [isMinimized, setIsMinimized] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [showFallback, setShowFallback] = useState(false);
    
    const notebookUrl = 'https://notebooklm.google.com/notebook/5e6b5313-d245-4fb6-b322-3fee8ed3d612';

    // Timeout 10 giây để LUÔN chuyển sang fallback
    useEffect(() => {
        const timer = setTimeout(() => {
            setIsLoading(false);
            setShowFallback(true);
        }, 6000); // 10 giây LUÔN chuyển

        return () => clearTimeout(timer);
    }, []);

    const handleRefresh = () => {
        setIsLoading(true);
        setShowFallback(false);
        
        // Clear iframe trước
        const iframe = document.getElementById('notebooklm-iframe');
        if (iframe) {
            iframe.src = 'about:blank';
        }
        
        // Reset timeout 10 giây mới - LUÔN chuyển sau 10s
        setTimeout(() => {
            setIsLoading(false);
            setShowFallback(true);
        }, 10000);
        
        // Reload iframe sau một chút
        setTimeout(() => {
            if (iframe) {
                iframe.src = notebookUrl;
            }
        }, 100);
    };

    const handleIframeLoad = () => {
        // Ngay cả khi iframe "load" (có thể là trang lỗi), vẫn để timeout handle
        // Không tắt loading ở đây vì Google sẽ redirect tới trang lỗi
        console.log('Iframe loaded - nhưng có thể là trang lỗi');
    };

    const openInNewTab = () => {
        window.open(notebookUrl, '_blank');
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('container')}>
                {/* Browser Header */}
                <div className={cx('browser-header')}>
                    <div className={cx('browser-controls')}>
                        <div className={cx('traffic-lights')}>
                            <FontAwesomeIcon icon={faCircle} className={cx('light', 'red')} />
                            <FontAwesomeIcon icon={faCircle} className={cx('light', 'yellow')} />
                            <FontAwesomeIcon icon={faCircle} className={cx('light', 'green')} />
                        </div>
                        <div className={cx('address-bar')}>
                            <div className={cx('url-display')}>
                                <FontAwesomeIcon icon={faRobot} className={cx('site-icon')} />
                                <span className={cx('url-text')}>notebooklm.google.com/notebook/...</span>
                            </div>
                        </div>
                    </div>
                    <div className={cx('browser-actions')}>
                        <button 
                            onClick={handleRefresh}
                            className={cx('action-btn')}
                            title="Refresh"
                        >
                            <FontAwesomeIcon icon={faRotateRight} />
                        </button>
                        <button 
                            onClick={openInNewTab}
                            className={cx('action-btn')}
                            title="Open in new tab"
                        >
                            <FontAwesomeIcon icon={faExternalLinkAlt} />
                        </button>
                        <button 
                            onClick={() => setIsMinimized(!isMinimized)}
                            className={cx('action-btn')}
                            title={isMinimized ? "Maximize" : "Minimize"}
                        >
                            <FontAwesomeIcon icon={isMinimized ? faPlus : faMinus} />
                        </button>
                    </div>
                </div>

                {/* Main Content */}
                {!isMinimized && (
                    <div className={cx('content-area')}>
                        {/* Loading Overlay */}
                        {isLoading && (
                            <div className={cx('loading-overlay')}>
                                <div className={cx('loading-spinner')}>
                                    <div className={cx('spinner')}></div>
                                    <p className={cx('loading-text')}>Đang tải NotebookLM...</p>
                                </div>
                            </div>
                        )}

                        {/* NotebookLM Header Info */}
                        <div className={cx('notebook-header')}>
                            <div className={cx('notebook-info')}>
                                <div className={cx('notebook-icon')}>
                                    <FontAwesomeIcon icon={faRobot} />
                                </div>
                                <div className={cx('notebook-details')}>
                                    <h3 className={cx('notebook-title')}>AI Chatbot Hỗ Trợ Thủ Tục Hành Chính</h3>
                                    <p className={cx('notebook-desc')}>
                                        Chatbot hỗ trợ dịch vụ công lĩnh vực Xuất nhập cảnh
                                    </p>
                                </div>
                            </div>
                            <div className={cx('notebook-status')}>
                                <div className={cx('status-dot')}></div>
                                <span>Sẵn sàng trò chuyện</span>
                            </div>
                        </div>

                        {/* Iframe hoặc Fallback */}
                        <div className={cx('iframe-container')}>
                            {!showFallback ? (
                                <iframe
                                    id="notebooklm-iframe"
                                    src={notebookUrl}
                                    className={cx('notebook-iframe')}
                                    title="NotebookLM Interface"
                                    onLoad={handleIframeLoad}
                                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                                />
                            ) : (
                                <div className={cx('access-notice')}>
                                    <div className={cx('notice-icon')}>
                                        <FontAwesomeIcon icon={faRobot} />
                                    </div>
                                    <div className={cx('notice-content')}>
                                        <h4 className={cx('notice-title')}>NotebookLM Ready</h4>
                                        <p className={cx('notice-desc')}>
                                            Do chính sách bảo mật của Google, NotebookLM không thể hiển thị tại đây. 
                                            Click vào nút bên dưới để mở NotebookLM trong tab mới.
                                        </p>
                                        <div className={cx('notice-features')}>
                                            <div className={cx('feature-item')}>
                                                <span className={cx('feature-icon')}>📄</span>
                                                <span>Tài liệu đã được upload</span>
                                            </div>
                                            <div className={cx('feature-item')}>
                                                <span className={cx('feature-icon')}>🤖</span>
                                                <span>AI sẵn sàng trả lời</span>
                                            </div>
                                            <div className={cx('feature-item')}>
                                                <span className={cx('feature-icon')}>💬</span>
                                                <span>Chat trực tiếp với tài liệu</span>
                                            </div>
                                        </div>
                                        <button 
                                            className={cx('access-btn')}
                                            onClick={openInNewTab}
                                        >
                                            <FontAwesomeIcon icon={faExternalLinkAlt} />
                                            <span>Mở NotebookLM</span>
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Footer Note */}
                        <div className={cx('footer-note')}>
                            <p>
                                💡 Bạn đang sử dụng NotebookLM để tư vấn chuyên sâu về các quy định của lĩnh vực Xuất nhập cảnh. 
                                Hãy đặt câu hỏi về các quy định của pháp luật, thủ tục hành chính để có thể hỗ trợ bạn tốt nhất.
                            </p>
                        </div>
                    </div>
                )}

                {/* Minimized State */}
                {isMinimized && (
                    <div className={cx('minimized-state')}>
                        <div className={cx('minimized-content')}>
                            <FontAwesomeIcon icon={faRobot} className={cx('minimized-icon')} />
                            <div className={cx('minimized-text')}>
                                <span className={cx('minimized-title')}>NotebookLM</span>
                                <span className={cx('minimized-subtitle')}>AI Document Analysis</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default NotebookLm;