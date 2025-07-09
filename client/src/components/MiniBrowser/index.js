import React, { useRef, useState, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './MiniBrowser.module.scss';

const cx = classNames.bind(styles);

const MiniBrowser = () => {
    const iframeRef = useRef(null);
    const [currentUrl, setCurrentUrl] = useState('');
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [showLoginPrompt, setShowLoginPrompt] = useState(true);
    const [errorMessage, setErrorMessage] = useState('');

    // URL mặc định
    const loginUrl =
        'https://xacthuc.dichvucong.gov.vn/oauth2/authorize?response_type=code&amp;client_id=Np0ahpF4exnI6DS_4KuMK_TLHLEa&amp;scope=openid&amp;redirect_uri=https://dichvucong.gov.vn/p/home/dvc-trang-chu.html';
    const applicationUrl =
        'https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/listThuTuc?co_quan_cha=&loai_co_quan=&co_quan_con=&linh_vuc=CAP_CCCD&muc_do=&tukhoa=&doi_tuong=&cap_thuc_hien=&co_quan_cuc=&co_quan_tinh=&co_quan_huyen=&co_quan_xa='; // Giả định URL nộp hồ sơ

    useEffect(() => {
        // Lắng nghe sự kiện thay đổi localStorage (nếu có)
        const handleStorageChange = (event) => {
            if (event.key === 'loginStatus' && event.newValue === 'success') {
                setIsLoggedIn(true);
                setCurrentUrl(applicationUrl);
                setShowLoginPrompt(false);
            }
        };

        window.addEventListener('storage', handleStorageChange);

        // Kiểm tra trạng thái đăng nhập khi component mount
        const loginStatus = localStorage.getItem('loginStatus');
        if (loginStatus === 'success') {
            setIsLoggedIn(true);
            setCurrentUrl(applicationUrl);
            setShowLoginPrompt(false);
        }

        // Cleanup
        return () => {
            window.removeEventListener('storage', handleStorageChange);
            setCurrentUrl('');
            setIsLoggedIn(false);
            setShowLoginPrompt(true);
        };
    }, [applicationUrl]);

    const handleLoginClick = (e) => {
        e.preventDefault();
        // Mở tab mới để đăng nhập
        window.open(loginUrl, '_blank');
        setShowLoginPrompt(false);
        setErrorMessage('Vui lòng đăng nhập trong tab mới. Sau khi đăng nhập, nhấn nút "Đã đăng nhập" bên dưới.');
    };

    const handleCheckLogin = () => {
        // Giả lập kiểm tra đăng nhập (vì không thể truy cập trực tiếp trang đăng nhập)
        // Trong thực tế, bạn có thể gọi API hoặc kiểm tra cookie nếu có
        setCurrentUrl(applicationUrl);
        setIsLoggedIn(true);
        setErrorMessage('');
    };

    const handleIframeLoad = () => {
        try {
            const iframeWindow = iframeRef.current?.contentWindow;
            if (iframeWindow) {
                const newUrl = iframeWindow.location.href;
                // Nếu iframe chuyển hướng về trang đăng nhập, báo lỗi
                if (newUrl.includes('dvc-trang-chu.html') && isLoggedIn) {
                    setErrorMessage('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.');
                    setIsLoggedIn(false);
                    setCurrentUrl('');
                    setShowLoginPrompt(true);
                }
            }
        } catch (error) {
            console.error('Error checking iframe URL:', error);
        }
    };

    return (
        <div className={cx('mini-browser-wrapper')}>
            {showLoginPrompt && (
                <div className={cx('login-button')}>
                    <a href={loginUrl} onClick={handleLoginClick}>
                        Đăng nhập Dịch vụ Công
                    </a>
                </div>
            )}
            {!showLoginPrompt && !isLoggedIn && (
                <div className={cx('login-check')}>
                    <button onClick={handleCheckLogin} className={cx('check-login')}>
                        Đã đăng nhập
                    </button>
                    {errorMessage && <p className={cx('error-message')}>{errorMessage}</p>}
                </div>
            )}
            {isLoggedIn && currentUrl && (
                <iframe
                    ref={iframeRef}
                    src={currentUrl}
                    onLoad={handleIframeLoad}
                    className={cx('iframe')}
                    title="Dịch vụ Công"
                ></iframe>
            )}
        </div>
    );
};

export default MiniBrowser;
