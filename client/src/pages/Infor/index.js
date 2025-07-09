import React from 'react';
import classNames from 'classnames/bind';
import styles from './Infor.module.scss';

const cx = classNames.bind(styles);

const Infor = () => {
    return (
        <div className={cx('infor-page')}>
            <div className={cx('container')}>
                <div className={cx('breadcrumb')}>
                    <ul>
                        <li>
                            <a href="/">Trang chủ</a>
                        </li>
                        <li>Giới thiệu</li>
                    </ul>
                </div>

                <div className={cx('content')}>
                    <h1 className={cx('page-title')}>Chatbot AI hỗ trợ thủ tục xuất nhập cảnh & cấp hộ chiếu</h1>

                    <div className={cx('intro-section')}>
                        <div className={cx('intro-text')}>
                            <p>
                                Trợ lý ảo thông minh chuyên hỗ trợ công dân trong các thủ tục liên quan đến xuất nhập cảnh, 
                                cấp hộ chiếu, visa và các dịch vụ lãnh sự. Cung cấp thông tin chính xác, hướng dẫn chi tiết 
                                từng bước thực hiện.
                            </p>
                            <p>
                                Hệ thống hoạt động 24/7, cập nhật thông tin mới nhất về quy định xuất nhập cảnh, 
                                giúp người dân chuẩn bị hồ sơ đúng và đầy đủ ngay từ lần đầu.
                            </p>
                        </div>
                        
                        <div className={cx('chatbot-demo')}>
                            <div className={cx('chat-window')}>
                                <div className={cx('chat-header')}>
                                    <span className={cx('bot-name')}>🤖 Trợ lý dịch vụ công</span>
                                    <span className={cx('status')}>• Đang hoạt động</span>
                                </div>
                                <div className={cx('chat-messages')}>
                                    <div className={cx('message', 'user-message')}>
                                        Tôi muốn làm hộ chiếu lần đầu
                                    </div>
                                    <div className={cx('message', 'bot-message')}>
                                        Để làm hộ chiếu lần đầu, bạn cần:
                                        <br />• CCCD gốc + photocopy
                                        <br />• Ảnh 4x6 nền trắng (6 tháng gần đây)
                                        <br />• Phí: 160.000đ 
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className={cx('features-section')}>
                        <h2>Tính năng chính</h2>
                        <div className={cx('features-grid')}>
                            <div className={cx('feature-item')}>
                                <h3>Hướng dẫn hộ chiếu</h3>
                                <p>Hướng dẫn chi tiết làm hộ chiếu thường, gấp, gia hạn và thủ tục liên quan</p>
                            </div>
                            <div className={cx('feature-item')}>
                                <h3>Thông tin visa</h3>
                                <p>Tư vấn visa các nước, yêu cầu hồ sơ và thời gian xử lý</p>
                            </div>
                            <div className={cx('feature-item')}>
                                <h3>Xuất nhập cảnh</h3>
                                <p>Quy định mới nhất về xuất nhập cảnh, thủ tục tại cửa khẩu</p>
                            </div>
                            <div className={cx('feature-item')}>
                                <h3>Tra cứu tiến độ</h3>
                                <p>Kiểm tra tình trạng xử lý hồ sơ hộ chiếu và các thủ tục khác</p>
                            </div>
                        </div>
                    </div>

                    <div className={cx('services-section')}>
                        <h2>Dịch vụ hỗ trợ</h2>
                        <div className={cx('services-grid')}>
                            <div className={cx('service-category')}>
                                <h3>Hộ chiếu & Giấy tờ</h3>
                                <ul>
                                    <li>Làm hộ chiếu lần đầu</li>
                                    <li>Gia hạn hộ chiếu</li>
                                    <li>Cấp lại hộ chiếu (mất, hỏng)</li>
                                    <li>Hộ chiếu cho trẻ em</li>
                                    <li>Hộ chiếu công vụ</li>
                                    <li>Giấy thông hành</li>
                                </ul>
                            </div>
                            <div className={cx('service-category')}>
                                <h3>Visa & Xuất nhập cảnh</h3>
                                <ul>
                                    <li>Visa du lịch</li>
                                    <li>Visa công tác</li>
                                    <li>Visa định cư</li>
                                    <li>Thủ tục xuất cảnh</li>
                                    <li>Thủ tục nhập cảnh</li>
                                    <li>Gia hạn tạm trú</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div className={cx('benefits-section')}>
                        <h2>Lợi ích</h2>
                        <div className={cx('benefits-list')}>
                            <div className={cx('benefit-item')}>
                                <span className={cx('benefit-icon')}>⏰</span>
                                <div>
                                    <strong>Tiết kiệm thời gian</strong>
                                    <p>Không cần đến trực tiếp cơ quan để hỏi thông tin</p>
                                </div>
                            </div>
                            <div className={cx('benefit-item')}>
                                <span className={cx('benefit-icon')}>💰</span>
                                <div>
                                    <strong>Giảm chi phí</strong>
                                    <p>Tiết kiệm chi phí đi lại và thời gian chờ đợi</p>
                                </div>
                            </div>
                            <div className={cx('benefit-item')}>
                                <span className={cx('benefit-icon')}>📝</span>
                                <div>
                                    <strong>Thông tin chính xác</strong>
                                    <p>Cập nhật từ nguồn chính thức của các cơ quan nhà nước</p>
                                </div>
                            </div>
                            <div className={cx('benefit-item')}>
                                <span className={cx('benefit-icon')}>📱</span>
                                <div>
                                    <strong>Dễ sử dụng</strong>
                                    <p>Giao diện đơn giản, phù hợp với mọi đối tượng</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className={cx('usage-guide')}>
                        <h2>Cách sử dụng</h2>
                        <div className={cx('steps')}>
                            <div className={cx('step')}>
                                <div className={cx('step-number')}>1</div>
                                <div className={cx('step-content')}>
                                    <h4>Đặt câu hỏi</h4>
                                    <p>Nhập câu hỏi về thủ tục bạn muốn thực hiện</p>
                                </div>
                            </div>
                            <div className={cx('step')}>
                                <div className={cx('step-number')}>2</div>
                                <div className={cx('step-content')}>
                                    <h4>Nhận hướng dẫn</h4>
                                    <p>Chatbot sẽ cung cấp thông tin chi tiết và hướng dẫn cụ thể</p>
                                </div>
                            </div>
                            <div className={cx('step')}>
                                <div className={cx('step-number')}>3</div>
                                <div className={cx('step-content')}>
                                    <h4>Thực hiện thủ tục</h4>
                                    <p>Làm theo hướng dẫn để hoàn thành thủ tục nhanh chóng</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className={cx('contact-section')}>
                        <h2>Hỗ trợ thêm</h2>
                        <p>
                            Nếu cần hỗ trợ thêm về thủ tục xuất nhập cảnh, bạn có thể liên hệ:
                        </p>
                        <ul className={cx('contact-list')}>
                            <li>Tổng đài: <strong>1900 xxxx</strong></li>
                            <li>Email: <strong>xuatnhapcanh@daklak</strong></li>
                            <li>Phòng Quản lý xuất nhập cảnh - Công an tỉnh Đắk Lắk</li>
                            <li>Thời gian: Thứ 2 - Thứ 6 (7:30 - 16:30)</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Infor;