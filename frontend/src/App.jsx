import { useEffect, useState, useRef } from 'react'
import { createChart, CandlestickSeries } from 'lightweight-charts'
import './App.css'

export default function App() {
  const [market, setMarket] = useState(null)
  const [candles, setCandles] = useState([])
  const [strategyLab, setStrategyLab] = useState([])
  const [parameterLab, setParameterLab] = useState([])
  const [evolutionLab, setEvolutionLab] = useState([])
  const [walkForwardLab, setWalkForwardLab] = useState([])
  const [researchDirector, setResearchDirector] = useState(null)
  const [tradeJournal, setTradeJournal] = useState(null)
  const [execution, setExecution] = useState({})
  const [equityCurve, setEquityCurve] = useState(null)
  const [liveStrategyPerformance, setLiveStrategyPerformance] = useState(null)
  const [tradeAnalytics, setTradeAnalytics] = useState(null)

  const chartRef = useRef()

  const fetchMarket = () => {
    fetch('http://127.0.0.1:8000/api/market-summary')
      .then((res) => res.json())
      .then((data) => setMarket(data))
      .catch((err) => console.error('Backend error:', err))
  }

  const loadExecutionEngine = () => {
    fetch('http://127.0.0.1:8000/api/ai-execution-engine')
      .then((res) => res.json())
      .then((data) => setExecution(data))
      .catch((err) => console.error('Execution engine error:', err))
  }

  useEffect(() => {
    const loadDashboard = () => {
      fetchMarket()
      loadExecutionEngine()
    }

    loadDashboard()

    const interval = setInterval(loadDashboard, 30000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/strategy-lab')
      .then((res) => res.json())
      .then((data) => setStrategyLab(data.strategies || []))
      .catch((err) => console.error('Strategy Lab error:', err))

    fetch('http://127.0.0.1:8000/api/parameter-lab')
      .then((res) => res.json())
      .then((data) => setParameterLab(data.parameter_tests || []))
      .catch((err) => console.error('Parameter Lab error:', err))

    fetch('http://127.0.0.1:8000/api/evolution-lab')
      .then((res) => res.json())
      .then((data) => setEvolutionLab(data.evolution_tests || []))
      .catch((err) => console.error('Evolution Lab error:', err))

    fetch('http://127.0.0.1:8000/api/walk-forward-lab')
      .then((res) => res.json())
      .then((data) => setWalkForwardLab(data.walk_forward_tests || []))
      .catch((err) => console.error('Walk Forward Lab error:', err))

    fetch('http://127.0.0.1:8000/api/research-director')
      .then((res) => res.json())
      .then((data) => setResearchDirector(data))
      .catch((err) => console.error('Research Director error:', err))

    fetch('http://127.0.0.1:8000/api/trade-journal')
      .then((res) => res.json())
      .then((data) => setTradeJournal(data))
      .catch((err) => console.error('Trade Journal error:', err))

    fetch('http://127.0.0.1:8000/api/equity-curve')
      .then((res) => res.json())
      .then((data) => setEquityCurve(data))
      .catch((err) => console.error('Equity Curve error:', err))

    fetch('http://127.0.0.1:8000/api/live-strategy-performance')
      .then((res) => res.json())
      .then((data) => setLiveStrategyPerformance(data))
      .catch((err) => console.error('Live strategy performance error:', err))

    fetch('http://127.0.0.1:8000/api/trade-analytics')
      .then((res) => res.json())
      .then((data) => setTradeAnalytics(data))
      .catch((err) => console.error('Trade analytics error:', err))
  }, [])

  useEffect(() => {
    const fetchCandles = () => {
      fetch('http://127.0.0.1:8000/api/candles')
        .then((res) => res.json())
        .then((data) => setCandles(data.candles || []))
        .catch((err) => console.error('Candle API error:', err))
    }

    fetchCandles()

    const interval = setInterval(fetchCandles, 30000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!chartRef.current || candles.length === 0) return

    chartRef.current.innerHTML = ''

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: chartRef.current.clientHeight || 260,
      layout: {
        background: { color: '#071120' },
        textColor: '#b8c5d5',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.05)' },
        horzLines: { color: 'rgba(255,255,255,0.05)' },
      },
      rightPriceScale: {
        borderColor: '#25344d',
      },
      timeScale: {
        borderColor: '#25344d',
        timeVisible: true,
      },
    })

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#00ff99',
      downColor: '#ff5577',
      borderVisible: false,
      wickUpColor: '#00ff99',
      wickDownColor: '#ff5577',
    })

    const formatted = candles
      .filter((c) => c.open && c.high && c.low && c.close && c.time)
      .map((c) => ({
        time: Math.floor(new Date(c.time.replace(' ', 'T')).getTime() / 1000),
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
      }))
      .filter((c) => Number.isFinite(c.time))

    candlestickSeries.setData(formatted)
    chart.timeScale().fitContent()

    return () => chart.remove()
  }, [candles])

  if (!market) {
    return <div className="loading">Loading HK50 data...</div>
  }

  return (
    <div className="terminal">
      <aside className="sidebar">
        <div className="brandCard">
          <div className="flag">🇭🇰</div>
          <div>
            <h2>HK50</h2>
            <p>^HSI</p>
          </div>
        </div>

        <p className="sectionLabel">CONSOLE</p>

        <nav>
          <a className="active">▧ Dashboard</a>
          <a>♧ Research</a>
          <a>◇ Trading</a>
          <a>▣ Analytics</a>
        </nav>

        <div className="systemStatus">
          <strong>SYSTEM STATUS</strong>
          <p>● All Systems Operational</p>
          <small>
            Data Source: Yahoo Finance
            <br />
            Mode: Paper Trading
          </small>
        </div>
      </aside>

      <main className="main">
        <header className="header">
          <div>
            <h1>
              HK50 AI Market Assistant <span>v4.3</span>
            </h1>
            <p>
              Research Director • Live Learning • Trade Analytics • Signal
              Execution
            </p>
          </div>

          <div className="statusCards">
            <div>
              <small>MARKET</small>
              <b className="green">{market.market_status} ↯</b>
            </div>

            <div>
              <small>LAST UPDATE</small>
              <b>{market.last_update}</b>
            </div>

            <div>
              <small>AUTO REFRESH</small>
              <b>{market.auto_refresh} ↻</b>
            </div>
          </div>
        </header>

        <section className="topGrid">
          <div className="summaryCard priceCard">
            <div className="cardTitle">HK50 PRICE</div>
            <h2>{market.price}</h2>
            <p className={market.change.includes('-') ? 'red' : 'green'}>
              {market.change}
            </p>
            <small>Live market pricing</small>
          </div>

          <div className="summaryCard">
            <div className="cardTitle">TREND</div>
            <h2 className={market.trend === 'Bearish' ? 'red' : 'green'}>
              {market.trend}
            </h2>
            <p>{market.trend_detail}</p>
            <small>
              Market confidence: <b className="yellow">{market.confidence}</b>
            </small>
          </div>

          <div className="summaryCard riskCard">
            <div className="cardTitle">RISK LEVEL</div>
            <h2 className="yellow">{market.risk}</h2>
            <p>{market.risk_detail}</p>
            <small>
              ATR: <b className="yellow">{market.atr_percent}%</b>
            </small>
          </div>
        </section>

        <section className="middleGrid">
          <div className="panel">
            <div className="panelTitle">LIVE STRATEGY LEADERBOARD</div>

            <table className="dataTable">
              <thead>
                <tr>
                  <th>RANK</th>
                  <th>STRATEGY</th>
                  <th>TRADES</th>
                  <th>WINS</th>
                  <th>LOSSES</th>
                  <th>WIN RATE</th>
                  <th>AVG RETURN</th>
                  <th>LIVE SCORE</th>
                </tr>
              </thead>

              <tbody>
                {liveStrategyPerformance?.strategies?.length > 0 ? (
                  liveStrategyPerformance.strategies.map((row, index) => (
                    <tr key={row.strategy}>
                      <td>{index + 1}</td>
                      <td>{row.strategy}</td>
                      <td>{row.total_trades}</td>
                      <td>{row.wins}</td>
                      <td>{row.losses}</td>
                      <td>{row.win_rate}%</td>
                      <td>{row.average_return}%</td>
                      <td>{row.live_score}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="8">No live strategy data yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <div className="panelTitle">RESEARCH DIRECTOR DECISION</div>

            <div className="executionGrid compact">
              <p>
                SELECTED STRATEGY{' '}
                <b>{researchDirector?.best_strategy || 'N/A'}</b>
              </p>

              <p>
                CONFIDENCE <b>{researchDirector?.confidence_score ?? 0}</b>
              </p>

              <p>
                LABEL <b>{researchDirector?.confidence_label || 'UNKNOWN'}</b>
              </p>

              <p>
                LIVE SCORE <b>{researchDirector?.live_score ?? 0}</b>
              </p>
            </div>

            <table className="dataTable">
              <thead>
                <tr>
                  <th>STRATEGY</th>
                  <th>SOURCE</th>
                  <th>LIVE</th>
                  <th>ANALYTICS</th>
                  <th>SCORE</th>
                </tr>
              </thead>

              <tbody>
                {researchDirector?.strategy_candidates?.length > 0 ? (
                  researchDirector.strategy_candidates
                    .slice(0, 5)
                    .map((candidate, index) => (
                      <tr key={index}>
                        <td>{candidate.strategy}</td>
                        <td>{candidate.source}</td>
                        <td>{candidate.live_bonus}</td>
                        <td>{candidate.analytics_bonus}</td>
                        <td>{candidate.final_score}</td>
                      </tr>
                    ))
                ) : (
                  <tr>
                    <td colSpan="3">No strategy candidates.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="chartGrid">
          <div className="chartPanel">
            <div className="chartTop">
              <div className="chartTitleRow">
                <strong>HK50 PRICE CHART (1H)</strong>

                <span>
                  Analytics:{' '}
                  {execution.trade_analytics_reason || 'No analytics update'}
                </span>
              </div>

              <div className="chartTabs">
                <span className="activeTab">1H</span>
                <span>Live</span>
              </div>
            </div>

            <div className="chartArea">
              <div
                ref={chartRef}
                style={{
                  width: '100%',
                  height: '100%',
                }}
              />
            </div>
          </div>
        </section>

        <section className="bottomGrid">
          <div className="bottomPanel">
            <div className="panelTitle">
              STRATEGY LAB <span>(Top Performers)</span>
            </div>

            <table>
              <thead>
                <tr>
                  <th>RANK</th>
                  <th>STRATEGY</th>
                  <th>TRADES</th>
                  <th>WIN RATE</th>
                  <th>RETURN</th>
                  <th>DRAWDOWN</th>
                  <th>SIGNAL</th>
                </tr>
              </thead>

              <tbody>
                {strategyLab.length > 0 ? (
                  strategyLab.map((strategy) => (
                    <tr key={strategy.rank}>
                      <td>{strategy.rank}</td>
                      <td>{strategy.strategy}</td>
                      <td>{strategy.trades}</td>
                      <td>{strategy.win_rate}%</td>
                      <td
                        className={strategy.total_return >= 0 ? 'green' : 'red'}
                      >
                        {strategy.total_return}%
                      </td>
                      <td
                        className={
                          strategy.max_drawdown < -5 ? 'red' : 'yellow'
                        }
                      >
                        {strategy.max_drawdown}%
                      </td>
                      <td
                        className={strategy.signal === 'BUY' ? 'green' : 'red'}
                      >
                        {strategy.signal}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7">Loading strategy lab...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="bottomPanel">
            <div className="panelTitle">
              PARAMETER LAB <span>(RSI Optimisation)</span>
            </div>

            <table>
              <thead>
                <tr>
                  <th>RANK</th>
                  <th>PARAMETER</th>
                  <th>TRADES</th>
                  <th>WIN RATE</th>
                  <th>RETURN</th>
                  <th>DRAWDOWN</th>
                  <th>SIGNAL</th>
                </tr>
              </thead>

              <tbody>
                {parameterLab.length > 0 ? (
                  parameterLab.map((test) => (
                    <tr key={test.rank}>
                      <td>{test.rank}</td>
                      <td>{test.parameter}</td>
                      <td>{test.trades}</td>
                      <td>{test.win_rate}%</td>
                      <td className={test.total_return >= 0 ? 'green' : 'red'}>
                        {test.total_return}%
                      </td>
                      <td className={test.max_drawdown < -5 ? 'red' : 'yellow'}>
                        {test.max_drawdown}%
                      </td>
                      <td className={test.signal === 'BUY' ? 'green' : 'red'}>
                        {test.signal}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7">Loading parameter lab...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="bottomPanel">
            <div className="panelTitle">
              EVOLUTION LAB <span>(AI Generated)</span>
            </div>

            <table>
              <thead>
                <tr>
                  <th>RANK</th>
                  <th>STRATEGY</th>
                  <th>TRADES</th>
                  <th>WIN RATE</th>
                  <th>RETURN</th>
                  <th>DRAWDOWN</th>
                  <th>SIGNAL</th>
                </tr>
              </thead>

              <tbody>
                {evolutionLab.length > 0 ? (
                  evolutionLab.slice(0, 6).map((test) => (
                    <tr key={test.rank}>
                      <td>{test.rank}</td>
                      <td>{test.strategy}</td>
                      <td>{test.trades}</td>
                      <td>{test.win_rate}%</td>
                      <td className={test.total_return >= 0 ? 'green' : 'red'}>
                        {test.total_return}%
                      </td>
                      <td className={test.max_drawdown < -5 ? 'red' : 'yellow'}>
                        {test.max_drawdown}%
                      </td>
                      <td className={test.signal === 'BUY' ? 'green' : 'red'}>
                        {test.signal}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7">Loading evolution lab...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="bottomPanel">
            <div className="panelTitle">
              WALK FORWARD LAB <span>(Validation)</span>
            </div>

            <table>
              <thead>
                <tr>
                  <th>RANK</th>
                  <th>STRATEGY</th>
                  <th>TRAIN</th>
                  <th>TEST</th>
                  <th>ROBUSTNESS</th>
                </tr>
              </thead>

              <tbody>
                {walkForwardLab.slice(0, 6).map((test) => (
                  <tr key={test.rank}>
                    <td>{test.rank}</td>
                    <td>{test.strategy}</td>
                    <td>{test.train_return}%</td>
                    <td>{test.test_return}%</td>
                    <td>{test.robustness}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bottomPanel">
            <div className="panelTitle">TRADE ANALYTICS</div>

            <div className="paperStats">
              <p>
                TOTAL TRADES <b>{tradeAnalytics?.total_trades ?? 0}</b>
              </p>

              <p>
                BEST STRATEGY{' '}
                <b className="green">
                  {tradeAnalytics?.strategy_performance?.[0]?.strategy || 'N/A'}
                </b>
              </p>

              <p>
                STRATEGY AVG RETURN{' '}
                <b className="green">
                  {tradeAnalytics?.strategy_performance?.[0]?.average_return?.toFixed?.(
                    2,
                  ) ?? 0}
                  %
                </b>
              </p>

              <p>
                BEST VOTE STRENGTH{' '}
                <b>
                  {tradeAnalytics?.vote_performance?.[0]?.vote_strength ??
                    'N/A'}
                </b>
              </p>

              <p>
                VOTE AVG RETURN{' '}
                <b className="green">
                  {tradeAnalytics?.vote_performance?.[0]?.result_pct?.toFixed?.(
                    2,
                  ) ?? 0}
                  %
                </b>
              </p>

              <p>
                BEST EXIT TYPE{' '}
                <b className="green">
                  {tradeAnalytics?.exit_performance?.[0]?.result || 'N/A'}
                </b>
              </p>

              <p>
                EXIT AVG RETURN{' '}
                <b className="green">
                  {tradeAnalytics?.exit_performance?.[0]?.result_pct?.toFixed?.(
                    2,
                  ) ?? 0}
                  %
                </b>
              </p>
            </div>
          </div>

          <div className="bottomPanel paperPanel">
            <div className="panelTitle">TRADING PERFORMANCE</div>

            <div className="paperStats">
              <p>
                TOTAL TRADES <b>{tradeJournal?.total_trades ?? 0}</b>
              </p>

              <p>
                WIN RATE{' '}
                <b
                  className={
                    (tradeJournal?.win_rate ?? 0) >= 50 ? 'green' : 'red'
                  }
                >
                  {tradeJournal?.win_rate ?? 0}%
                </b>
              </p>

              <p>
                AVG RETURN{' '}
                <b
                  className={
                    (tradeJournal?.average_return ?? 0) >= 0 ? 'green' : 'red'
                  }
                >
                  {tradeJournal?.average_return ?? 0}%
                </b>
              </p>

              <p>
                BEST TRADE{' '}
                <b className="green">{tradeJournal?.best_trade ?? 0}%</b>
              </p>

              <p>
                WORST TRADE{' '}
                <b
                  className={
                    (tradeJournal?.worst_trade ?? 0) >= 0 ? 'green' : 'red'
                  }
                >
                  {tradeJournal?.worst_trade ?? 0}%
                </b>
              </p>

              <p>
                CURRENT EQUITY{' '}
                <b
                  className={
                    (equityCurve?.total_return ?? 0) >= 0 ? 'green' : 'red'
                  }
                >
                  ${equityCurve?.current_equity?.toLocaleString() ?? 0}
                </b>
              </p>

              <p>
                TOTAL RETURN{' '}
                <b
                  className={
                    (equityCurve?.total_return ?? 0) >= 0 ? 'green' : 'red'
                  }
                >
                  {equityCurve?.total_return ?? 0}%
                </b>
              </p>

              <p>
                MAX DRAWDOWN{' '}
                <b className="red">{equityCurve?.max_drawdown ?? 0}%</b>
              </p>
            </div>
          </div>

          <div className="bottomPanel aiExecutionPanel">
            <div className="panelTitle">AI TRADE DECISION</div>

            <div className="executionGrid">
              <p>
                STRATEGY{' '}
                <b>
                  {execution.strategy?.strategy || execution.strategy || 'N/A'}
                </b>
              </p>

              <p>
                FINAL SIGNAL <b>{execution.final_signal || 'N/A'}</b>
              </p>

              <p>
                AI QUALITY
                <b>
                  {execution.quality ||
                    execution.position_size?.quality ||
                    'UNKNOWN'}
                </b>
              </p>

              <p>
                POSITION SIZE{' '}
                <b>
                  {execution.position_size?.position_size_label || 'UNKNOWN'}
                </b>
              </p>

              <p>
                CONFIDENCE <b>{execution.confidence ?? 0}</b>
              </p>

              <p>
                QUALITY BONUS <b>{execution.quality_analytics_bonus ?? 0}</b>
              </p>

              <p>
                VOTE SIGNAL <b>{execution.vote_signal || 'UNKNOWN'}</b>
              </p>

              <p>
                VOTE STRENGTH{' '}
                <b>
                  {execution.vote_strength ?? 0}/{execution.total_votes ?? 0}
                </b>
              </p>

              <p>
                MARKET CONFIDENCE <b>{execution.market_confidence ?? 0}</b>
              </p>

              <p>
                RESEARCH CONFIDENCE <b>{execution.research_confidence ?? 0}</b>
              </p>

              <p>
                RISK PER TRADE{' '}
                <b>{execution.position_size?.risk_per_trade_percent ?? 0}%</b>
              </p>

              <p>
                EXPOSURE{' '}
                <b>
                  {execution.position_size?.suggested_exposure_percent ?? 0}%
                </b>
              </p>

              <p>
                OPEN POSITION <b>{execution.open_position || 'NONE'}</b>
              </p>

              <p>
                PEAK PROFIT <b>{execution.peak_profit_percent ?? 0}%</b>
              </p>

              <p>
                TRAILING ACTIVE{' '}
                <b>{execution.trailing_active ? 'YES' : 'NO'}</b>
              </p>

              <p>
                TRACKER <b>{execution.tracker_status || 'IDLE'}</b>
                <p>
                  MARKET REGIME <b>{execution.market_regime || 'UNKNOWN'}</b>
                </p>
                <p>
                  ACTIVE STRATEGY{' '}
                  <b>{execution.rotation_selected_strategy || 'N/A'}</b>
                </p>
                <p>
                  RESEARCH STRATEGY{' '}
                  <b>{execution.rotation_original_strategy || 'N/A'}</b>
                </p>
                <p>
                  ROTATION{' '}
                  <b>{execution.rotation_changed_strategy ? 'YES' : 'NO'}</b>
                </p>
              </p>
            </div>

            <div className="executionReason">
              <p>
                <b>QUALITY LEARNING:</b>{' '}
                {execution.quality_analytics_reason ||
                  'No quality learning data yet'}
              </p>

              <p>
                <b>AI REASON:</b> {execution.reason || 'No reason available'}
              </p>
            </div>

            <div className="executionReason">
              {execution.reason}
              <br />
              <br />
              RAW SIGNAL:{' '}
              {execution.raw_signal ||
                execution.raw_strategy_signal ||
                'Not available'}
              <br />
              FINAL SIGNAL: {execution.final_signal || 'Not available'}
              <br />
              VOTING ASSIST: {execution.voting_assist_reason || 'Not available'}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
