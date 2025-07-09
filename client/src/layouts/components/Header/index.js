import React, { useRef, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './Header.module.scss';
import images from '~/assets/images';

const cx = classNames.bind(styles);

const Header = ({ currentPage }) => {
    const navRef = useRef(null);

    // Auto detect current page from URL if not provided
    const getCurrentPage = () => {
        if (currentPage) return currentPage;

        const path = window.location.pathname;
        if (path === '/') return 'home';
        if (path.includes('gioi-thieu')) return 'about';
        if (path.includes('tro-ly-ao') || path.includes('chatbot')) return 'chatbot';
        if (path.includes('gop-y')) return 'feedback';
        return 'home';
    };

    const activePage = getCurrentPage();

    useEffect(() => {
        // Remove active class from all nav links
        if (navRef.current) {
            const navLinks = navRef.current.querySelectorAll('a');
            navLinks.forEach((link) => link.classList.remove(cx('active')));

            // Add active class to current page
            const pageMap = {
                home: '/',
                about: '/gioi-thieu',
                chatbot: '/tro-ly-ao',
                feedback: '/gop-y',
            };

            const targetHref = pageMap[activePage];
            if (targetHref) {
                const activeLink = navRef.current.querySelector(`a[href="${targetHref}"]`);
                if (activeLink) {
                    activeLink.classList.add(cx('active'));
                }
            }
        }
    }, [activePage, cx]);

    return (
        <header
            className={cx('header')}
            style={{
                backgroundImage: `url(${images.backgroundHeader})`,
            }}
        >
            <div className={cx('container')}>
                <div className={cx('content')}>
                    {/* Logo và Text */}
                    <div className={cx('logo-section')}>
                        <a href="/" className={cx('logo')}>
                            <img src={images.logo} alt="Chatbot hỗ trợ Dịch vụ công" className={cx('logo-img')} />
                        </a>
                        <div className={cx('text')}>
                            <h1 className={cx('title')}>HƯỚNG DẪN DỊCH VỤ CÔNG</h1>
                            <p className={cx('subtitle')}>
                                Đồng hành cùng người dân, doanh nghiệp bước vào kỷ nguyên mới
                            </p>
                        </div>
                    </div>

                    {/* Navigation Menu - Giữa */}
                    <nav className={cx('nav')} ref={navRef}>
                        <a href="/" className={cx('nav-link')}>
                            <span className={cx('icon')} role="img" aria-label="home">
                                🏠
                            </span>
                            Trang chủ
                        </a>
                        <a href="/gioi-thieu" className={cx('nav-link')}>
                            Giới thiệu
                        </a>
                        <a href="/tro-ly-ao" className={cx('nav-link')}>
                            Chatbot
                        </a>
                        <a href="/gop-y" className={cx('nav-link')}>
                            Góp ý
                        </a>
                        <a href="/notebooklm" className={cx('nav-link')}>
                            Chuyên gia
                        </a>
                    </nav>

                    {/* Auth Buttons - Góc phải */}
                    <div className={cx('auth-buttons')}>
                        <a href="/register" className={cx('btn', 'btn-register')}>
                            Đăng ký
                        </a>
                        <a href="/login" className={cx('btn', 'btn-login')}>
                            Đăng nhập
                        </a>
                    </div>

                    {/* Mobile Menu Button */}
                    {/* <button className={cx('mobile-menu-btn')}>
                        <svg className={cx('menu-icon')} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    </button> */}
                </div>
            </div>
        </header>
    );
};

export default Header;
