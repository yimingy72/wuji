import { Link } from 'react-router-dom';
import { stateLabel, type DemoTaskState } from './model';
import styles from '../prototype.module.css';

export function Status({ state }: { state: DemoTaskState }) {
  return <span className={styles.status} data-state={state}><span className={styles.statusDot} aria-hidden="true" />{stateLabel[state]}</span>;
}

export function Notice({ title, body }: { title: string; body: string }) {
  return <section className={styles.notice} role="status"><h1>{title}</h1><p>{body}</p><Link to="/tasks">返回任务列表</Link></section>;
}
