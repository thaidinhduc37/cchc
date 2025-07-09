import React, { useState, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './Virtualassistant.module.scss';
import Chatbot from '~/components/Chatbot';
import RightPanel from '~/components/RightPanel';

const cx = classNames.bind(styles);

const Virtualassistant = () => {
    // TẠO USERID STABLE thay vì tạo mới mỗi render
    const [userId] = useState(() => `user_${Date.now()}`);
    
    // State để chia sẻ data giữa Chatbot và RightPanel - MOVED BEFORE USAGE
    const [sharedData, setSharedData] = useState({
        currentStep: null,
        flowData: null,
        guideImage: null,
        guideInfo: null
    });

    // Callback để nhận data từ Chatbot qua useChatbot
    const handleDataUpdate = (data) => {
        console.log('📥 Virtualassistant received data from Chatbot:', data);
        setSharedData(prevData => ({
            ...prevData,
            ...data
        }));
    };

    // Setup global callback cho Chatbot (backup method)
    useEffect(() => {
        window.onChatbotDataUpdate = handleDataUpdate;
        
        return () => {
            delete window.onChatbotDataUpdate;
        };
    }, []);

    // Debug log khi sharedData thay đổi
    useEffect(() => {
        console.log('🔄 SharedData updated in Virtualassistant:', {
            currentStep: sharedData.currentStep,
            hasFlowData: !!sharedData.flowData,
            hasImage: !!sharedData.guideImage,
            hasGuideInfo: !!sharedData.guideInfo
        });
    }, [sharedData]);

    return (
        <div className={cx('virtualassistant-wrapper')}>
            <div className={cx('content')}>
                <div className={cx('chatbot-container')}>
                    <Chatbot 
                        userId={userId}
                        onDataUpdate={handleDataUpdate}  // TRUYỀN CALLBACK VÀO CHATBOT
                    />
                </div>
                <div className={cx('right-panel-container')}>
                    <RightPanel 
                        userId={userId}
                        currentStep={sharedData.currentStep}      // TRUYỀN DỮ LIỆU VÀO RIGHTPANEL
                        flowData={sharedData.flowData}
                        guideImage={sharedData.guideImage}
                        guideInfo={sharedData.guideInfo}
                    />
                </div>
            </div>
        </div>
    );
};

export default Virtualassistant;