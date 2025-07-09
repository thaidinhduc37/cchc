import { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Feedback.module.scss';

const cx = classNames.bind(styles);

function Feedback() {
    const [fullName, setFullName] = useState('');
    const [phone, setPhone] = useState('');
    const [email, setEmail] = useState('');
    const [feedback, setFeedback] = useState('');
    const [success, setSuccess] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState({});

    // Simple validation
    const validateField = (name, value) => {
        switch (name) {
            case 'fullName':
                return !value.trim() ? 'Vui lòng nhập họ và tên' : '';
            case 'phone':
                return !value.trim()
                    ? 'Vui lòng nhập số điện thoại'
                    : !/^[0-9]{10,11}$/.test(value.replace(/\s/g, ''))
                    ? 'Số điện thoại không hợp lệ'
                    : '';
            case 'email':
                return !value.trim()
                    ? 'Vui lòng nhập email'
                    : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
                    ? 'Email không hợp lệ'
                    : '';
            case 'feedback':
                return !value.trim() ? 'Vui lòng nhập nội dung phản hồi' : '';
            default:
                return '';
        }
    };

    const handleInputChange = (name, value) => {
        switch (name) {
            case 'fullName':
                setFullName(value);
                break;
            case 'phone':
                setPhone(value);
                break;
            case 'email':
                setEmail(value);
                break;
            case 'feedback':
                setFeedback(value);
                break;
        }

        // Clear error when user types
        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: '' }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validate all fields
        const newErrors = {};
        newErrors.fullName = validateField('fullName', fullName);
        newErrors.phone = validateField('phone', phone);
        newErrors.email = validateField('email', email);
        newErrors.feedback = validateField('feedback', feedback);

        const hasErrors = Object.values(newErrors).some((error) => error !== '');

        if (hasErrors) {
            setErrors(newErrors);
            return;
        }

        setIsSubmitting(true);

        try {
            // Simulate API call
            await new Promise((resolve) => setTimeout(resolve, 1500));

            setSuccess(true);
            setFullName('');
            setPhone('');
            setEmail('');
            setFeedback('');
            setErrors({});

            setTimeout(() => setSuccess(false), 4000);
        } catch (error) {
            console.error('Submission error:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('feedback-box')}>
                <div className={cx('header')}>
                    <div className={cx('logo')}>🏛️</div>
                    <h1 className={cx('title')}>Báo lỗi hoặc góp ý</h1>
                    <p className={cx('desc')}>
                        Sự đóng góp ý kiến từ các bạn sẽ là sự hỗ trợ đắc lực giúp chúng tôi ngày càng hoàn thiện sản
                        phẩm tốt hơn.
                    </p>
                </div>

                <form className={cx('form')} onSubmit={handleSubmit}>
                    {/* Full Name */}
                    <div className={cx('input-group')}>
                        <input
                            className={cx('input', { error: errors.fullName })}
                            type="text"
                            placeholder="Họ và tên *"
                            value={fullName}
                            onChange={(e) => handleInputChange('fullName', e.target.value)}
                            disabled={isSubmitting}
                        />
                        {errors.fullName && <div className={cx('error-message')}>{errors.fullName}</div>}
                    </div>

                    {/* Phone */}
                    <div className={cx('input-group')}>
                        <input
                            className={cx('input', { error: errors.phone })}
                            type="tel"
                            placeholder="Số điện thoại *"
                            value={phone}
                            onChange={(e) => handleInputChange('phone', e.target.value)}
                            disabled={isSubmitting}
                        />
                        {errors.phone && <div className={cx('error-message')}>{errors.phone}</div>}
                    </div>

                    {/* Email */}
                    <div className={cx('input-group')}>
                        <input
                            className={cx('input', { error: errors.email })}
                            type="email"
                            placeholder="Email của bạn *"
                            value={email}
                            onChange={(e) => handleInputChange('email', e.target.value)}
                            disabled={isSubmitting}
                        />
                        {errors.email && <div className={cx('error-message')}>{errors.email}</div>}
                    </div>

                    {/* Feedback */}
                    <div className={cx('input-group')}>
                        <textarea
                            className={cx('textarea', { error: errors.feedback })}
                            rows={5}
                            placeholder="Nhập phản hồi của bạn tại đây! *"
                            value={feedback}
                            onChange={(e) => handleInputChange('feedback', e.target.value)}
                            disabled={isSubmitting}
                        />
                        {errors.feedback && <div className={cx('error-message')}>{errors.feedback}</div>}
                    </div>

                    {/* Submit Button */}
                    <button className={cx('submit')} type="submit" disabled={isSubmitting}>
                        {isSubmitting ? (
                            <>
                                <span className={cx('loading-spinner')}></span>
                                Đang gửi...
                            </>
                        ) : (
                            'GỬI Ý KIẾN'
                        )}
                    </button>

                    {/* Success Message */}
                    {success && (
                        <div className={cx('success')}>
                            ✅ Cảm ơn bạn đã góp ý! Chúng tôi sẽ tiếp thu phản hồi của bạn sớm nhất.
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
}

export default Feedback;
