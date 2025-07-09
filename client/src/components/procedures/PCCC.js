import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './Procedures.module.scss';
import flowData from '../../domains/pccc/flow.json';

const cx = classNames.bind(styles);

function PCCC() {
    const [currentQuestion, setCurrentQuestion] = useState(flowData.questions[0]);
    const [currentFlow, setCurrentFlow] = useState(null);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);

    const handleOptionSelect = (option) => {
        if (option.next) {
            const nextQuestion = flowData.questions.find((q) => q.id === option.next);
            setCurrentQuestion(nextQuestion);
        } else if (option.flow) {
            setCurrentFlow(flowData.flows[option.flow]);
            setCurrentStepIndex(0);
        }
    };

    const handleBack = () => {
        if (currentFlow) {
            if (currentStepIndex > 0) {
                setCurrentStepIndex(currentStepIndex - 1);
            } else {
                setCurrentFlow(null);
                setCurrentStepIndex(0);
            }
        } else {
            const prevQuestion = flowData.questions.find((q) =>
                q.options.some((opt) => opt.next === currentQuestion.id),
            );
            setCurrentQuestion(prevQuestion || flowData.questions[0]);
        }
    };

    const handleNext = () => {
        if (currentFlow && currentStepIndex < currentFlow.steps.length - 1) {
            setCurrentStepIndex(currentStepIndex + 1);
        }
    };

    const renderStep = (stepId) => {
        const step = flowData.steps[stepId.split('.')[0]];
        if (!step) return null;

        if (typeof step === 'string') {
            return <p className={cx('step-content')}>{step}</p>;
        }

        return (
            <div className={cx('step-content')}>
                <p className={cx('step-name')}>{step.name}</p>
                {stepId.includes('.') && step.substeps && <p className={cx('step-detail')}>{step.substeps[stepId]}</p>}
            </div>
        );
    };

    const renderContent = () => {
        if (currentFlow) {
            const currentStep = currentFlow.steps[currentStepIndex];
            return (
                <div className={cx('details')}>
                    <h3>{currentFlow.name}</h3>
                    <div className={cx('info-card')}>
                        <div className={cx('step-number')}>
                            Bước {currentStepIndex + 1}/{currentFlow.steps.length}
                        </div>
                        {renderStep(currentStep)}
                    </div>
                    <div className={cx('footer')}>
                        <button onClick={handleBack}>Quay lại</button>
                        {currentStepIndex < currentFlow.steps.length - 1 ? (
                            <button className={cx('primary')} onClick={handleNext}>
                                Tiếp tục
                            </button>
                        ) : (
                            <button className={cx('primary')}>Hoàn thành</button>
                        )}
                    </div>
                </div>
            );
        }

        return (
            <div className={cx('select')}>
                <p>{currentQuestion.question}</p>
                <div className={cx('options')}>
                    {currentQuestion.options.map((option, index) => (
                        <button key={index} onClick={() => handleOptionSelect(option)}>
                            {option.label}
                        </button>
                    ))}
                </div>
                {currentQuestion.id !== 'registration_type' && (
                    <div className={cx('footer')}>
                        <button onClick={handleBack}>Quay lại</button>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className={cx('wrapper')}>
            <h2>Thủ tục PCCC</h2>
            {renderContent()}
        </div>
    );
}

export default PCCC;
