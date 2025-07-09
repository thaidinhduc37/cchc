import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Procedures.module.scss';

const cx = classNames.bind(styles);

function DangKyXe() {
    const [stage, setStage] = useState('init');
    const [procedureType, setProcedureType] = useState(null);

    const handleOptionSelect = (type) => {
        setProcedureType(type);
        setStage('selectScenario');
    };

    const handleBack = () => {
        setStage('init');
        setProcedureType(null);
    };

    const renderContent = () => {
        switch (stage) {
            case 'init':
                return (
                    <div className={cx('select')}>
                        <p>Bạn đang thuộc trường hợp nào dưới đây?</p>
                        <div className={cx('options')}>
                            <button onClick={() => handleOptionSelect('register')}>Đăng ký xe mới</button>
                            <button onClick={() => handleOptionSelect('transfer')}>Sang tên xe</button>
                            <button onClick={() => handleOptionSelect('change')}>Thay đổi thông tin</button>
                        </div>
                    </div>
                );
            case 'selectScenario':
                return (
                    <div className={cx('select')}>
                        <p>Chọn trường hợp cụ thể:</p>
                        <select className={cx('select-input')}>
                            <option value="" disabled selected>
                                -- Chọn --
                            </option>
                            {procedureType === 'register' && (
                                <>
                                    <option value="motorcycle">Đăng ký xe máy</option>
                                    <option value="car">Đăng ký ô tô</option>
                                </>
                            )}
                            {procedureType === 'transfer' && (
                                <>
                                    <option value="motorcycle">Sang tên xe máy</option>
                                    <option value="car">Sang tên ô tô</option>
                                </>
                            )}
                            {procedureType === 'change' && (
                                <>
                                    <option value="owner">Thay đổi chủ xe</option>
                                    <option value="color">Thay đổi màu sơn</option>
                                    <option value="engine">Thay đổi động cơ</option>
                                </>
                            )}
                        </select>
                        <div className={cx('footer')}>
                            <button onClick={handleBack}>◀ Quay lại</button>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className={cx('wrapper')}>
            <h2>Thủ tục Đăng ký xe</h2>
            {renderContent()}
        </div>
    );
}

export default DangKyXe;
