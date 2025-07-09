import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Home.module.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faRobot, faBolt, faArrowRight } from '@fortawesome/free-solid-svg-icons';

const cx = classNames.bind(styles);

const Home = () => {
    const [searchQuery, setSearchQuery] = useState('');

    return (
        <div className={cx('home')}>
            {/* Hero Section - Compact */}
            <section className={cx('hero')}>
                <div className={cx('container')}>
                    <div className={cx('hero-content')}>
                        <div className={cx('ai-badge')}>
                            <FontAwesomeIcon icon={faRobot} />
                            <span>AI Chatbot</span>
                            <div className={cx('pulse-dot')}></div>
                        </div>

                        <h1 className={cx('hero-title')}>
                            CHATBOT HỖ TRỢ DỊCH VỤ CÔNG
                            <span className={cx('subtitle')}>Dịch vụ công Bộ Công an</span>
                        </h1>

                        <p className={cx('hero-desc')}>Trợ lý AI thông minh • Phản hồi tức thì • Hỗ trợ 24/7</p>
                    </div>
                </div>
            </section>

            {/* Search Bar */}
            <div className={cx('search-section')}>
                <div className={cx('container')}>
                    <div className={cx('search-box')}>
                        <FontAwesomeIcon icon={faRobot} className={cx('search-icon')} />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Hỏi AI về thủ tục, pháp luật... VD: Cấp Hộ chiếu trên Cổng Dịch vụ công?"
                            className={cx('search-input')}
                        />
                        <button className={cx('search-btn')}>
                            <FontAwesomeIcon icon={faBolt} />
                            <span>Hỏi AI</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Services Grid */}
            <div className={cx('services')}>
                <div className={cx('container')}>
                    <h2 className={cx('section-title')}>Dịch vụ AI hỗ trợ</h2>

                    <div className={cx('services-grid')}>
                        <button className={cx('service-card', 'card-1')}>
                            <span className={cx('card-emoji')}>🏛️</span>
                            <span className={cx('card-text')}>Dịch vụ Công Quốc gia</span>
                            <FontAwesomeIcon icon={faArrowRight} className={cx('card-arrow')} />
                        </button>

                        <button className={cx('service-card', 'card-2')}>
                            <span className={cx('card-emoji')}>🛡️</span>
                            <span className={cx('card-text')}>Dịch vụ công Bộ Công an</span>
                            <FontAwesomeIcon icon={faArrowRight} className={cx('card-arrow')} />
                        </button>

                        <button className={cx('service-card', 'card-3')}>
                            <span className={cx('card-emoji')}>🏢</span>
                            <span className={cx('card-text')}>Xuất nhập cảnh</span>
                            <FontAwesomeIcon icon={faArrowRight} className={cx('card-arrow')} />
                        </button>

                        <button className={cx('service-card', 'card-4', 'ai-special')}>
                            <span className={cx('card-emoji')}>🤖</span>
                            <span className={cx('card-text')}>AI Pháp luật</span>
                            <div className={cx('ai-tag')}>AI</div>
                            <FontAwesomeIcon icon={faArrowRight} className={cx('card-arrow')} />
                        </button>

                        <button className={cx('service-card', 'card-5')}>
                            <span className={cx('card-emoji')}>📢</span>
                            <span className={cx('card-text')}>Phản ánh chính sách</span>
                            <FontAwesomeIcon icon={faArrowRight} className={cx('card-arrow')} />
                        </button>

                        <button className={cx('service-card', 'card-6')}>
                            <span className={cx('card-emoji')}>💼</span>
                            <span className={cx('card-text')}>Hỗ trợ doanh nghiệp</span>
                            <FontAwesomeIcon icon={faArrowRight} className={cx('card-arrow')} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Footer */}
            {/* <div className={cx('footer')}>
                <div className={cx('container')}>
                    <div className={cx('footer-content')}>
                        <div className={cx('footer-brand')}>
                            <FontAwesomeIcon icon={faRobot} />
                            <span>AI Chatbot Đắk Lắk</span>
                        </div>
                        <div className={cx('footer-info')}>
                            Hỗ trợ 24/7 • xuatnhapcanh@daklak.gov.vn
                        </div>
                    </div>
                </div>
            </div> */}
        </div>
    );
};

export default Home;
