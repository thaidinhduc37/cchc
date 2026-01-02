import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Auth.module.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEye, faEyeSlash, faEnvelope, faLock, faUser, faPhone, faCheck } from '@fortawesome/free-solid-svg-icons';
import {
    faGoogle as faGoogleBrand,
    faFacebook as faFacebookBrand,
    faApple as faAppleBrand,
} from '@fortawesome/free-brands-svg-icons';
import { useNavigate } from 'react-router-dom';
import authService from '~/api/authService';

const cx = classNames.bind(styles);

const Register = () => {
    const [formData, setFormData] = useState({
        fullName: '',
        email: '',
        phone: '',
        password: '',
        confirmPassword: '',
        agreeTerms: false,
    });
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const navigate = useNavigate();

    const validateField = (name, value) => {
        switch (name) {
            case 'fullName':
                return !value.trim()
                    ? 'Họ và tên không được để trống'
                    : value.trim().length < 2
                    ? 'Họ và tên phải có ít nhất 2 ký tự'
                    : '';
            case 'email':
                return !value.trim()
                    ? 'Email không được để trống'
                    : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
                    ? 'Email không hợp lệ'
                    : '';
            case 'phone':
                return !value.trim()
                    ? 'Số điện thoại không được để trống'
                    : !/^[0-9]{10,11}$/.test(value.replace(/\s/g, ''))
                    ? 'Số điện thoại không hợp lệ'
                    : '';
            case 'password':
                return !value.trim()
                    ? 'Mật khẩu không được để trống'
                    : value.length < 8
                    ? 'Mật khẩu phải có ít nhất 8 ký tự'
                    : !/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(value)
                    ? 'Mật khẩu phải chứa chữ hoa, chữ thường và số'
                    : '';
            case 'confirmPassword':
                return !value.trim()
                    ? 'Vui lòng xác nhận mật khẩu'
                    : value !== formData.password
                    ? 'Mật khẩu xác nhận không khớp'
                    : '';
            case 'agreeTerms':
                return !value ? 'Vui lòng đồng ý với điều khoản sử dụng' : '';
            default:
                return '';
        }
    };

    const handleInputChange = (name, value) => {
        setFormData((prev) => ({ ...prev, [name]: value }));

        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: '' }));
        }

        // Re-validate confirm password when password changes
        if (name === 'password' && formData.confirmPassword) {
            const confirmError = validateField('confirmPassword', formData.confirmPassword);
            if (confirmError !== errors.confirmPassword) {
                setErrors((prev) => ({ ...prev, confirmPassword: confirmError }));
            }
        }
    };

    const getPasswordStrength = (password) => {
        if (!password) return { strength: 0, text: '' };

        let strength = 0;
        const checks = [
            password.length >= 8,
            /[a-z]/.test(password),
            /[A-Z]/.test(password),
            /\d/.test(password),
            /[!@#$%^&*(),.?":{}|<>]/.test(password),
        ];

        strength = checks.filter(Boolean).length;

        const strengthLevels = {
            0: { text: '', color: '' },
            1: { text: 'Rất yếu', color: 'very-weak' },
            2: { text: 'Yếu', color: 'weak' },
            3: { text: 'Trung bình', color: 'medium' },
            4: { text: 'Mạnh', color: 'strong' },
            5: { text: 'Rất mạnh', color: 'very-strong' },
        };

        return { strength, ...strengthLevels[strength] };
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        const newErrors = {};
        Object.keys(formData).forEach((key) => {
            newErrors[key] = validateField(key, formData[key]);
        });

        if (Object.values(newErrors).some((error) => error !== '')) {
            setErrors(newErrors);
            return;
        }

        setIsSubmitting(true);

        try {
            // Chỉ gửi các field cần thiết lên API
            const userData = {
                email: formData.email,
                password: formData.password,
                fullname: formData.fullName,
                phone: formData.phone,
            };

            const response = await fetch('http://localhost:5000/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Đăng ký thất bại');
            }

            // Lưu token vào localStorage
            localStorage.setItem('access_token', data.access_token);

            // Redirect to dashboard
            navigate('/dashboard');
        } catch (error) {
            console.error('Registration error:', error);
            setErrors({
                submit: error.message || 'Đăng ký thất bại, vui lòng thử lại',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSocialLogin = (provider) => {
        console.log(`Register with ${provider}`);
        // Handle social registration
    };

    const passwordStrength = getPasswordStrength(formData.password);

    return (
        <div className={cx('auth-wrapper')}>
            <div className={cx('auth-container')}>
                <div className={cx('auth-card', 'register-card')}>
                    {/* Header */}
                    <div className={cx('auth-header')}>
                        <div className={cx('logo-section')}>
                            <div className={cx('logo')}>🏛️</div>
                            <h1 className={cx('title')}>Đăng ký tài khoản</h1>
                        </div>
                        <p className={cx('subtitle')}>Tạo tài khoản để trải nghiệm đầy đủ dịch vụ của chúng tôi.</p>
                    </div>

                    {/* Social Login */}
                    <div className={cx('social-section')}>
                        <button
                            type="button"
                            className={cx('social-btn', 'google')}
                            onClick={() => handleSocialLogin('google')}
                        >
                            <FontAwesomeIcon icon={faGoogleBrand} />
                            <span>Đăng ký với Google</span>
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

                    {/* Register Form */}
                    <form className={cx('auth-form')} onSubmit={handleSubmit}>
                        {/* Full Name Field */}
                        <div className={cx('input-group')}>
                            <label className={cx('label')}>Họ và tên</label>
                            <div className={cx('input-wrapper')}>
                                <FontAwesomeIcon icon={faUser} className={cx('input-icon')} />
                                <input
                                    type="text"
                                    className={cx('input', { error: errors.fullName })}
                                    placeholder="Nhập họ và tên đầy đủ"
                                    value={formData.fullName}
                                    onChange={(e) => handleInputChange('fullName', e.target.value)}
                                    disabled={isSubmitting}
                                />
                            </div>
                            {errors.fullName && <div className={cx('error-message')}>{errors.fullName}</div>}
                        </div>

                        {/* Email and Phone Row */}
                        <div className={cx('input-row')}>
                            <div className={cx('input-group', 'half')}>
                                <label className={cx('label')}>Email</label>
                                <div className={cx('input-wrapper')}>
                                    <FontAwesomeIcon icon={faEnvelope} className={cx('input-icon')} />
                                    <input
                                        type="email"
                                        className={cx('input', { error: errors.email })}
                                        placeholder="email@example.com"
                                        value={formData.email}
                                        onChange={(e) => handleInputChange('email', e.target.value)}
                                        disabled={isSubmitting}
                                    />
                                </div>
                                {errors.email && <div className={cx('error-message')}>{errors.email}</div>}
                            </div>

                            <div className={cx('input-group', 'half')}>
                                <label className={cx('label')}>Số điện thoại</label>
                                <div className={cx('input-wrapper')}>
                                    <FontAwesomeIcon icon={faPhone} className={cx('input-icon')} />
                                    <input
                                        type="tel"
                                        className={cx('input', { error: errors.phone })}
                                        placeholder="0123456789"
                                        value={formData.phone}
                                        onChange={(e) => handleInputChange('phone', e.target.value)}
                                        disabled={isSubmitting}
                                    />
                                </div>
                                {errors.phone && <div className={cx('error-message')}>{errors.phone}</div>}
                            </div>
                        </div>

                        {/* Password Field */}
                        <div className={cx('input-group')}>
                            <label className={cx('label')}>Mật khẩu</label>
                            <div className={cx('input-wrapper')}>
                                <FontAwesomeIcon icon={faLock} className={cx('input-icon')} />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    className={cx('input', { error: errors.password })}
                                    placeholder="Tạo mật khẩu mạnh"
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
                            {/* Password Strength Indicator */}
                            {formData.password && (
                                <div className={cx('password-strength')}>
                                    <div className={cx('strength-bar')}>
                                        <div
                                            className={cx('strength-fill', passwordStrength.color)}
                                            style={{ width: `${(passwordStrength.strength / 5) * 100}%` }}
                                        />
                                    </div>
                                    <span className={cx('strength-text', passwordStrength.color)}>
                                        {passwordStrength.text}
                                    </span>
                                </div>
                            )}
                            {errors.password && <div className={cx('error-message')}>{errors.password}</div>}
                        </div>

                        {/* Confirm Password Field */}
                        <div className={cx('input-group')}>
                            <label className={cx('label')}>Xác nhận mật khẩu</label>
                            <div className={cx('input-wrapper')}>
                                <FontAwesomeIcon icon={faLock} className={cx('input-icon')} />
                                <input
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    className={cx('input', { error: errors.confirmPassword })}
                                    placeholder="Nhập lại mật khẩu"
                                    value={formData.confirmPassword}
                                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                                    disabled={isSubmitting}
                                />
                                <button
                                    type="button"
                                    className={cx('password-toggle')}
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                >
                                    <FontAwesomeIcon icon={showConfirmPassword ? faEyeSlash : faEye} />
                                </button>
                            </div>
                            {errors.confirmPassword && (
                                <div className={cx('error-message')}>{errors.confirmPassword}</div>
                            )}
                        </div>

                        {/* Terms Agreement */}
                        <div className={cx('input-group')}>
                            <label className={cx('checkbox-wrapper', 'terms-wrapper')}>
                                <input
                                    type="checkbox"
                                    checked={formData.agreeTerms}
                                    onChange={(e) => handleInputChange('agreeTerms', e.target.checked)}
                                    disabled={isSubmitting}
                                />
                                <span className={cx('checkmark')}></span>
                                <span className={cx('checkbox-label')}>
                                    Tôi đồng ý với
                                    <button type="button" className={cx('terms-link')}>
                                        Điều khoản sử dụng
                                    </button>
                                    và
                                    <button type="button" className={cx('terms-link')}>
                                        Chính sách bảo mật
                                    </button>
                                </span>
                            </label>
                            {errors.agreeTerms && <div className={cx('error-message')}>{errors.agreeTerms}</div>}
                        </div>

                        {/* Submit Button */}
                        <button type="submit" className={cx('submit-btn')} disabled={isSubmitting}>
                            {isSubmitting ? (
                                <>
                                    <span className={cx('loading-spinner')}></span>
                                    Đang tạo tài khoản...
                                </>
                            ) : (
                                <>
                                    <FontAwesomeIcon icon={faCheck} />
                                    Tạo tài khoản
                                </>
                            )}
                        </button>
                    </form>

                    {/* Footer */}
                    <div className={cx('auth-footer')}>
                        <p>
                            Đã có tài khoản?
                            <a href="/login" className={cx('switch-link')}>
                                Đăng nhập ngay
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

export default Register;
