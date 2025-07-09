import React from 'react';
import classNames from 'classnames/bind';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faHouseChimney, faAngleRight } from '@fortawesome/free-solid-svg-icons';

import styles from './Breadcrumb.module.scss';

const cx = classNames.bind(styles);

function Breadcrumb({ data, title }) {
    const categories = data ? data.category : [];
    const type = data ? data.type : '';
    let typeGenre = [];
    switch (type) {
        case 'hoathinh':
            typeGenre = ['phim-hoat-hinh', 'Phim Hoạt Hình'];
            break;
        case 'series':
            typeGenre = ['phim-bo', 'Phim Bộ'];
            break;
        case 'single':
            typeGenre = ['phim-le', 'Phim Lẻ'];
            break;
        case 'tvshows':
            typeGenre = ['tv-shows', 'TV Show'];
            break;
        default:
            typeGenre = ['', ''];
            break;
    }

    return data ? (
        <ul className={cx('breadcrumb')} itemscope itemtype="https://schema.org/BreadcrumbList">
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <a itemprop="item" href="/" title="Xem phim">
                    <span itemprop="name">
                        <FontAwesomeIcon className={cx('fa')} icon={faHouseChimney} /> Xem phim
                        <FontAwesomeIcon className={cx('fa')} icon={faAngleRight} />
                    </span>
                </a>
                <meta itemprop="position" content="1" />
            </li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <a itemprop="item" href={`https://phimmoichill2.net/genre/${typeGenre[0]}`} title={typeGenre[1]}>
                    <span itemprop="name">
                        {typeGenre[1]}
                        <FontAwesomeIcon className={cx('fa')} icon={faAngleRight} />
                    </span>
                </a>
                <meta itemprop="position" content="2" />
            </li>
            {categories.length > 0 && (
                <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                    <a
                        itemprop="item"
                        href={`https://phimmoichill2.net/genre/${categories[0].slug}`}
                        title={categories[0].name}
                    >
                        <span itemprop="name">
                            {`Phim ${categories[0].name}`}
                            <FontAwesomeIcon className={cx('fa')} icon={faAngleRight} />
                        </span>
                    </a>
                    <meta itemprop="position" content="3" />
                </li>
            )}
            <li>{data.name}</li>
        </ul>
    ) : (
        <ul className={cx('breadcrumb')} itemscope itemtype="https://schema.org/BreadcrumbList">
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <a itemprop="item" href="/" title="Phim mới">
                    <span itemprop="name">
                        <FontAwesomeIcon className={cx('fa')} icon={faHouseChimney} /> Phim Mới
                        <FontAwesomeIcon className={cx('fa')} icon={faAngleRight} />
                    </span>
                </a>
                <meta itemprop="position" content="1" />
            </li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                    <h3 itemprop="name" className={cx('no-data')}>{title}</h3>
                <meta itemprop="position" content="2" />
            </li>
        </ul>
    );
}

export default Breadcrumb;
