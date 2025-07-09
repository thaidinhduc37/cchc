import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Auth.module.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
    faEye, 
    faEyeSlash, 
    faEnvelope, 
    faLock
} from '@fortawesome/free-solid-svg-icons';
import { 
    faGoogle as faGoogleBrand, 
    faFacebook as faFacebookBrand, 
    faApple as faAppleBrand
} from '@fortawesome/free-brands-svg-icons';

const cx = classNames.bind(styles);

const LogIn = () => {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        rememberMe: false
    });
    const [showPassword, setShowPassword] = useState(false);
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const validateField = (name, value) => {
        switch (name) {
            case 'email':
                return !value.trim() ? 'Email không được để trống' : 
                       !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? 'Email không hợp lệ' : '';
            case 'password':
                return !value.trim() ? 'Mật khẩu không được để trống' : 
                       value.length < 6 ? 'Mật khẩu phải có ít nhất 6 ký tự' : '';
            default:
                return '';
        }
    };

    const handleInputChange = (name, value) => {
        setFormData(prev => ({ ...prev, [name]: value }));
        
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: '' }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        const newErrors = {};
        newErrors.email = validateField('email', formData.email);
        newErrors.password = validateField('password', formData.password);

        const hasErrors = Object.values(newErrors).some(error => error !== '');
        
        if (hasErrors) {
            setErrors(newErrors);
            return;
        }

        setIsSubmitting(true);
        
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            console.log('Login successful:', formData);
            // Handle successful login here
            
        } catch (error) {
            console.error('Login error:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSocialLogin = (provider) => {
        console.log(`Login with ${provider}`);
        // Handle social login
    };

    return (
        <div className={cx('auth-wrapper')}>
            <div className={cx('auth-container')}>
                <div className={cx('auth-card')}>
                    {/* Header */}
                    <div className={cx('auth-header')}>
                        <div className={cx('logo-section')}>
                            <div className={cx('logo')}>🏛️</div>
                            <h1 className={cx('title')}>Đăng nhập</h1>
                        </div>
                        <p className={cx('subtitle')}>
                            Chào mừng bạn quay lại! Vui lòng đăng nhập để tiếp tục.
                        </p>
                    </div>

                    {/* Social Login */}
                    <div className={cx('social-section')}>
                        <button 
                            type="button"
                            className={cx('social-btn', 'google')}
                            onClick={() => handleSocialLogin('google')}
                        >
                            <FontAwesomeIcon icon={faGoogleBrand} />
                            <span>Tiếp tục với Google</span>
                        </button>
                        
                        <div className={cx('social-grid')}>
                            <button 
                                type="button"
                                className={cx('social-btn-small', 'facebook')}
                                onClick={() => handleSocialLogin('facebook')}
                                data-label="Facebook"
                            >
                                <FontAwesomeIcon icon={faFacebookBrand} />
                            </button>
                            <button 
                                type="button"
                                className={cx('social-btn-small', 'apple')}
                                onClick={() => handleSocialLogin('apple')}
                                data-label="Apple"
                            >
                                <FontAwesomeIcon icon={faAppleBrand} />
                            </button>
                        </div>
                    </div>

                    {/* Divider */}
                    <div className={cx('divider')}>
                        <span>hoặc</span>
                    </div>

                    {/* Login Form */}
                    <form className={cx('auth-form')} onSubmit={handleSubmit}>
                        {/* Email Field */}
                        <div className={cx('input-group')}>
                            <label className={cx('label')}>Email</label>
                            <div className={cx('input-wrapper')}>
                                <FontAwesomeIcon icon={faEnvelope} className={cx('input-icon')} />
                                <input
                                    type="email"
                                    className={cx('input', { error: errors.email })}
                                    placeholder="Nhập email của bạn"
                                    value={formData.email}
                                    onChange={(e) => handleInputChange('email', e.target.value)}
                                    disabled={isSubmitting}
                                />
                            </div>
                            {errors.email && (
                                <div className={cx('error-message')}>{errors.email}</div>
                            )}
                        </div>

                        {/* Password Field */}
                        <div className={cx('input-group')}>
                            <label className={cx('label')}>Mật khẩu</label>
                            <div className={cx('input-wrapper')}>
                                <FontAwesomeIcon icon={faLock} className={cx('input-icon')} />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    className={cx('input', { error: errors.password })}
                                    placeholder="Nhập mật khẩu"
                                    value={formData.password}
                                    onChange={(e) => handleInputChange('password', e.target.value)}
                                    disabled={isSubmitting}
                                />
                                <button
                                    type="button"
                                    className={cx('password-toggle')}
                                    onClick={() => setShowPassword(!showPassword)}
                                >
                                    <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} />
                                </button>
                            </div>
                            {errors.password && (
                                <div className={cx('error-message')}>{errors.password}</div>
                            )}
                        </div>

                        {/* Remember Me & Forgot Password */}
                        <div className={cx('form-options')}>
                            <label className={cx('checkbox-wrapper')}>
                                <input
                                    type="checkbox"
                                    checked={formData.rememberMe}
                                    onChange={(e) => handleInputChange('rememberMe', e.target.checked)}
                                    disabled={isSubmitting}
                                />
                                <span className={cx('checkmark')}></span>
                                <span className={cx('checkbox-label')}>Ghi nhớ đăng nhập</span>
                            </label>
                            <button type="button" className={cx('forgot-link')}>
                                Quên mật khẩu?
                            </button>
                        </div>

                        {/* Submit Button */}
                        <button 
                            type="submit" 
                            className={cx('submit-btn')}
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? (
                                <>
                                    <span className={cx('loading-spinner')}></span>
                                    Đang đăng nhập...
                                </>
                            ) : (
                                'Đăng nhập'
                            )}
                        </button>
                    </form>

                    {/* Footer */}
                    <div className={cx('auth-footer')}>
                        <p>
                            Chưa có tài khoản? 
                            <a href="/register" className={cx('switch-link')}>
                                Đăng ký ngay
                            </a>
                        </p>
                    </div>
                </div>

                {/* Background Pattern */}
                <div className={cx('bg-pattern')}></div>
            </div>
        </div>
    );
};

export default LogIn;