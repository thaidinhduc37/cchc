import classNames from 'classnames/bind';
import styles from './Search.module.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons';

const cx = classNames.bind(styles);

function Search() {
    return (
        <form method='GET' className={cx('search')} action='tìm-kiem/'>
            <input placeholder="Tìm tên phim, diễn viên..." type="text" className={cx('search-input')}></input>
            <button className={cx('search-btn')} >
                <FontAwesomeIcon icon={faMagnifyingGlass}></FontAwesomeIcon>
            </button>
        </form>
    );
}

export default Search;
