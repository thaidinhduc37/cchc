import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Procedures.module.scss';

const cx = classNames.bind(styles);

function HoChieu() {
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
                            <button onClick={() => handleOptionSelect('new')}>Cấp hộ chiếu lần đầu</button>
                            <button onClick={() => handleOptionSelect('renew')}>Gia hạn hộ chiếu</button>
                            <button onClick={() => handleOptionSelect('replace')}>Cấp lại hộ chiếu</button>
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
                            {procedureType === 'new' && (
                                <>
                                    <option value="normal">Cấp hộ chiếu phổ thông</option>
                                    <option value="urgent">Cấp hộ chiếu khẩn</option>
                                </>
                            )}
                            {procedureType === 'renew' && (
                                <>
                                    <option value="normal">Gia hạn hộ chiếu thông thường</option>
                                    <option value="urgent">Gia hạn hộ chiếu khẩn</option>
                                </>
                            )}
                            {procedureType === 'replace' && (
                                <>
                                    <option value="lost">Hộ chiếu bị mất</option>
                                    <option value="damaged">Hộ chiếu bị hư hỏng</option>
                                    <option value="full">Hộ chiếu hết trang</option>
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
            <h2>Thủ tục Hộ chiếu</h2>
            {renderContent()}
        </div>
    );
}

export default HoChieu;
