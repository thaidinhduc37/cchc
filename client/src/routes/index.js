import config from '~/config';
//Page
import Home from '~/pages/Home';
import Infor from '~/pages/Infor';
import Virtualassistant from '~/pages/Virtualassistant';
import Feedback from '~/pages/Feedback';
import Register from '~/pages/Auth/Register';
import Login from '~/pages/Auth/LogIn';
import NotebookLm from '~/pages/NotebookLm';

// Public Route
const publicRoutes = [
    { path: config.routes.home, component: Home },
    { path: config.routes.infor, component: Infor },
    { path: config.routes.virtualassistant, component: Virtualassistant },
    { path: config.routes.feedback, component: Feedback },
    { path: config.routes.register, component: Register },
    { path: config.routes.login, component: Login },
    { path: config.routes.notebooklm, component: NotebookLm },
];

const privateRoutes = [];

export { publicRoutes, privateRoutes };
