import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Procedures.module.scss';

const cx = classNames.bind(styles);

function LyLichTuPhap() {
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
                            <button onClick={() => handleOptionSelect('first')}>Cấp lần đầu</button>
                            <button onClick={() => handleOptionSelect('renew')}>Cấp lại</button>
                            <button onClick={() => handleOptionSelect('urgent')}>Cấp khẩn</button>
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
                            {procedureType === 'first' && (
                                <>
                                    <option value="normal">Cấp phiếu lý lịch tư pháp thông thường</option>
                                    <option value="number1">Cấp phiếu lý lịch tư pháp số 1</option>
                                    <option value="number2">Cấp phiếu lý lịch tư pháp số 2</option>
                                </>
                            )}
                            {procedureType === 'renew' && (
                                <>
                                    <option value="normal">Cấp lại phiếu lý lịch tư pháp thông thường</option>
                                    <option value="number1">Cấp lại phiếu lý lịch tư pháp số 1</option>
                                    <option value="number2">Cấp lại phiếu lý lịch tư pháp số 2</option>
                                </>
                            )}
                            {procedureType === 'urgent' && (
                                <>
                                    <option value="normal">Cấp khẩn phiếu lý lịch tư pháp thông thường</option>
                                    <option value="number1">Cấp khẩn phiếu lý lịch tư pháp số 1</option>
                                    <option value="number2">Cấp khẩn phiếu lý lịch tư pháp số 2</option>
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
            <h2>Thủ tục Lý lịch tư pháp</h2>
            {renderContent()}
        </div>
    );
}

export default LyLichTuPhap;
