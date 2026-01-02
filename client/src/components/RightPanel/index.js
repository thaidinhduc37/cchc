import React, { useState, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './RightPanel.module.scss';

const cx = classNames.bind(styles);

const RightPanel = ({ userId, currentStep = null, flowData = null, guideImage = null, guideInfo = null }) => {
    const [activeTab, setActiveTab] = useState('guide');
    const [faqs, setFaqs] = useState([]);

    // Initialize FAQs
    useEffect(() => {
        const defaultFaqs = [
            {
                question: 'Cần chuẩn bị những giấy tờ gì để làm hộ chiếu?',
                answer: 'Bạn cần có CCCD/Căn cước, giấy khai sinh (với trẻ em), và các giấy tờ liên quan khác tùy theo trường hợp.',
            },
            {
                question: 'Thời gian làm hộ chiếu bao lâu?',
                answer: 'Thời gian làm hộ chiếu thông thường là 08 ngày làm việc kể từ ngày nộp hồ sơ đầy đủ.',
            },
            {
                question: 'Chi phí làm hộ chiếu là bao nhiêu?',
                answer: 'Lệ phí làm hộ chiếu phổ thông là 100.000 VNĐ đối với hộ chiếu cấp mới, cấp đổi do hết hạn và 200.000 VNĐ đối với hộ chiếu cấp lại, cấp đổi do hư hỏng.',
            },
            {
                question: 'Có thể làm hộ chiếu online không?',
                answer: 'Có, bạn có thể nộp hồ sơ trực tuyến qua Cổng dịch vụ công của Bộ Công an.',
            },
        ];
        setFaqs(defaultFaqs);
    }, []);

    // DEBUG: Log khi nhận data mới
    useEffect(() => {
        console.log('🔍 RightPanel received data update:', {
            currentStep,
            flowData,
            guideImage,
            guideInfo,
            timestamp: new Date().toLocaleTimeString(),
        });
    }, [currentStep, flowData, guideImage, guideInfo]);

    const renderGuideContent = () => {
        // FIXED: Xác định đang trong flow
        const isInFlow = currentStep !== null && flowData !== null;

        console.log('🎯 Flow status check:', {
            currentStep,
            flowData: !!flowData,
            isInFlow,
            hasGuideImage: !!guideImage,
        });

        return (
            <div className={cx('guide-content')}>
                {/* FIXED: Logic hiển thị ảnh */}
                <div className={cx('guide-placeholder')}>
                    {/* Hiển thị ảnh CHỈ KHI đang trong flow VÀ có ảnh */}
                    {isInFlow && guideImage ? (
                        <img
                            key={guideImage}
                            src={guideImage}
                            alt={`Hướng dẫn ${currentStep ? `bước ${currentStep}` : ''}`}
                            className={cx('guide-main-image')}
                            onLoad={() => {
                                console.log('✅ Image loaded successfully:', guideImage);
                            }}
                            onError={(e) => {
                                console.error('❌ Image loading error:', e.target.src);
                                e.target.style.display = 'none';

                                // Hiển thị placeholder khi lỗi ảnh
                                if (
                                    e.target.parentNode &&
                                    !e.target.parentNode.querySelector('.image-error-placeholder')
                                ) {
                                    const placeholder = document.createElement('div');
                                    placeholder.className = 'image-error-placeholder';
                                    placeholder.innerHTML = `
                                        <div style="text-align: center; padding: 40px; color: #666;">
                                            <h4>📸 Ảnh hướng dẫn</h4>
                                            <p>Không thể tải ảnh này</p>
                                        </div>
                                    `;
                                    e.target.parentNode.appendChild(placeholder);
                                }
                            }}
                        />
                    ) : isInFlow && !guideImage ? (
                        // Trong flow nhưng không có ảnh
                        <div
                            className={cx('no-image-placeholder')}
                            style={{
                                textAlign: 'center',
                                padding: '40px',
                                color: '#666',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'center',
                                alignItems: 'center',
                                minHeight: '200px',
                            }}
                        >
                            <h4>📸 Ảnh hướng dẫn</h4>
                            <p>Bước {currentStep || 'hiện tại'} chưa có ảnh minh họa</p>
                        </div>
                    ) : (
                    
                        <div
                            className={cx('default-placeholder')}
                            style={{
                                textAlign: 'center',
                                padding: '40px',
                                color: '#666',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'center',
                                alignItems: 'center',
                                minHeight: '200px',
                            }}
                        >
                            <h4>🗂️ Hướng dẫn quy trình</h4>
                            <p>
                                Để có thể thuận tiện hướng dẫn, bạn hãy nhập "Hướng dẫn tôi cấp ...... trực tuyến" bên
                                Chatbot Dịch vụ công
                            </p>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className={cx('right-panel')}>
            <div className={cx('header')}>
                <div className={cx('tabs')}>
                    <button
                        className={cx('tab', { active: activeTab === 'guide' })}
                        onClick={() => setActiveTab('guide')}
                    >
                        🗂️ Hướng dẫn
                    </button>
                    <button
                        className={cx('tab', { active: activeTab === 'info' })}
                        onClick={() => setActiveTab('info')}
                    >
                        ℹ️ Thông tin
                    </button>
                    <button
                        className={cx('tab', { active: activeTab === 'history' })}
                        onClick={() => setActiveTab('history')}
                    >
                        📜 Lịch sử
                    </button>
                    <button
                        className={cx('tab', { active: activeTab === 'settings' })}
                        onClick={() => setActiveTab('settings')}
                    >
                        ⚙️ Cài đặt
                    </button>
                </div>
            </div>

            <div className={cx('content')}>
                {activeTab === 'guide' && (
                    <div className={cx('guide-panel')}>
                        {renderGuideContent()}

                        {/* FAQs Section */}
                        <div className={cx('faqs-section')}>
                            <h4>❓ Câu hỏi thường gặp</h4>
                            <div className={cx('faq-list')}>
                                {faqs.map((faq, index) => (
                                    <details key={index} className={cx('faq-item')}>
                                        <summary className={cx('faq-question')}>{faq.question}</summary>
                                        <div className={cx('faq-answer')}>{faq.answer}</div>
                                    </details>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'info' && (
                    <div className={cx('info-panel')}>
                        <h3>🤖 Chatbot hỗ trợ Dịch vụ công</h3>
                        <div className={cx('info-item')}>
                            <span className={cx('label')}>Trạng thái:</span>
                            <span className={cx('value', 'online')}>🟢 Trực tuyến</span>
                        </div>
                        <div className={cx('info-item')}>
                            <span className={cx('label')}>Phiên bản:</span>
                            <span className={cx('value')}>v1.1.0</span>
                        </div>
                        <div className={cx('info-item')}>
                            <span className={cx('label')}>Ngôn ngữ:</span>
                            <span className={cx('value')}>🇻🇳 Tiếng Việt</span>
                        </div>

                        <div className={cx('quick-actions')}>
                            <h4>🚀 Thao tác nhanh</h4>
                            <button className={cx('action-btn')}>🗑️ Xóa lịch sử chat</button>
                            <button className={cx('action-btn')}>📤 Xuất dữ liệu</button>
                            <button className={cx('action-btn')}>🐛 Báo cáo lỗi</button>
                        </div>
                    </div>
                )}

                {activeTab === 'history' && (
                    <div className={cx('history-panel')}>
                        <h3>📜 Lịch sử cuộc trò chuyện</h3>
                        <div className={cx('history-list')}>
                            <div className={cx('history-item')}>
                                <div className={cx('history-title')}>🗂️ Hướng dẫn làm hộ chiếu</div>
                                <div className={cx('history-time')}>2 phút trước</div>
                            </div>
                            <div className={cx('history-item')}>
                                <div className={cx('history-title')}>📋 Quy trình dịch vụ công</div>
                                <div className={cx('history-time')}>15 phút trước</div>
                            </div>
                            <div className={cx('history-item')}>
                                <div className={cx('history-title')}>❓ Câu hỏi về thủ tục</div>
                                <div className={cx('history-time')}>1 giờ trước</div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'settings' && (
                    <div className={cx('settings-panel')}>
                        <h3>⚙️ Cài đặt</h3>
                        <div className={cx('setting-group')}>
                            <label className={cx('setting-label')}>
                                <input type="checkbox" defaultChecked />
                                🔊 Bật thông báo âm thanh
                            </label>
                            <label className={cx('setting-label')}>
                                <input type="checkbox" defaultChecked />
                                💾 Tự động lưu cuộc trò chuyện
                            </label>
                            <label className={cx('setting-label')}>
                                <input type="checkbox" />
                                🌙 Chế độ tối
                            </label>
                        </div>

                        <div className={cx('setting-group')}>
                            <label>🌐 Ngôn ngữ giao diện:</label>
                            <select className={cx('select-input')}>
                                <option value="vi">🇻🇳 Tiếng Việt</option>
                                <option value="en">🇺🇸 English</option>
                            </select>
                        </div>

                        <div className={cx('setting-group')}>
                            <label>📝 Kích thước font:</label>
                            <select className={cx('select-input')}>
                                <option value="small">Nhỏ</option>
                                <option value="medium">Vừa</option>
                                <option value="large">Lớn</option>
                            </select>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default RightPanel;
