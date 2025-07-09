import React from 'react';
import classNames from 'classnames/bind';
import styles from './Footer.module.scss';
import { MdEmail, MdPhone, MdLocationOn } from 'react-icons/md';

const cx = classNames.bind(styles);

const Footer = () => {
    return (
        <footer className={cx('footer')}>
            <div className={cx('container')}>
                <div className={cx('footer-content')}>
                    {/* Left - Organization */}
                    <div className={cx('org-section')}>
                        <h3 className={cx('title')}>🤖 Chatbot Hỗ trợ DVC</h3>
                        <p className={cx('subtitle')}>Đội Công nghệ thông tin - Phòng Tham mưu</p>
                    </div>

                    {/* Center - Contact */}
                    <div className={cx('contact-section')}>
                        <div className={cx('contact-item')}>
                            <MdLocationOn className={cx('icon')} />
                            <span>Công an tỉnh Đắk Lắk - 58 Nguyễn Tất Thành, TP. Buôn Ma Thuột, Đắk Lắk</span>
                        </div>
                        <div className={cx('contact-item')}>
                            <MdPhone className={cx('icon')} />
                            <span>Hotline: 18001096</span>
                        </div>
                        <div className={cx('contact-item')}>
                            <MdEmail className={cx('icon')} />
                            <a href="mailto:cntt.pv01.cat@dala.bca">cntt.pv01.cat@dala.bca</a>
                        </div>
                    </div>

                    {/* Right - Copyright */}
                    <div className={cx('copyright-section')}>
                        <p>© 2024 - Đội CNTT Phòng Tham mưu</p>
                        <p className={cx('source')}>
                            Khi sử dụng lại thông tin, đề nghị ghi rõ nguồn
                        </p>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;