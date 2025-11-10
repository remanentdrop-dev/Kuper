import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="3D Data Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🎯 3D Анализ данных: Промо vs Фулфилмент vs GMV")
    st.markdown("---")
    
    # File upload section
    st.sidebar.header("📁 Загрузка данных")
    uploaded_file = st.sidebar.file_uploader(
        "Загрузите CSV файл", 
        type=['csv'],
        help="Файл должен содержать необходимые колонки для анализа"
    )
    
    if uploaded_file is not None:
        try:
            # Read the CSV file
            df = pd.read_csv(uploaded_file)
            st.sidebar.success(f"✅ Файл загружен! Строк: {len(df)}")
            
            # Show data preview
            with st.sidebar.expander("🔍 Предпросмотр данных"):
                st.write(f"Колонки: {df.columns.tolist()}")
                st.write(f"Первые 5 строк:")
                st.dataframe(df.head())
            
            # Check required columns - более гибкая проверка
            required_columns = ['CP1 - ads', 'Orders delivered', 'Promo', 'GMV NoP - ads', 'Direct fullfillment']
            optional_columns = ['user_id', 'shipment_id', 'retailer_name', 'city_category', 'NRR', 'dt', 'flag', 'type_store_delivery']
            
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                st.error(f"❌ Отсутствуют обязательные колонки: {missing_required}")
                st.info("""
                **Необходимые колонки для анализа:**
                - CP1 - ads
                - Orders delivered  
                - Promo
                - GMV NoP - ads
                - Direct fullfillment
                """)
                return
            
            # Initialize session state
            if 'current_filtered_data' not in st.session_state:
                st.session_state.current_filtered_data = None
            if 'current_entity_name' not in st.session_state:
                st.session_state.current_entity_name = None
            
            # Setup filters
            setup_interactive_filters(df)
            
        except Exception as e:
            st.error(f"❌ Ошибка при чтении файла: {str(e)}")
            st.info("Попробуйте проверить формат CSV файла")
    else:
        st.info("👆 Пожалуйста, загрузите CSV файл в боковой панели чтобы начать анализ")
        
        # Show expected data structure
        with st.expander("📋 Ожидаемая структура данных"):
            st.markdown("""
            **Обязательные колонки:**
            - `CP1 - ads`: Расходы на рекламу
            - `Orders delivered`: Доставленные заказы
            - `Promo`: Промо расходы
            - `GMV NoP - ads`: GMV без рекламы
            - `Direct fullfillment`: Фулфилмент расходы
            
            **Опциональные колонки (для фильтрации):**
            - `user_id`: ID пользователя
            - `shipment_id`: ID отгрузки  
            - `retailer_name`: Название ритейлера
            - `city_category`: Категория города
            - `NRR`: Целевая группа NRR
            - `dt`: Дата
            - `flag`: Флаг/сегмент
            - `type_store_delivery`: Тип доставки
            """)

def setup_interactive_filters(df):
    """Настройка интерактивных фильтров в Streamlit"""
    
    st.sidebar.header("🎛️ Фильтры")
    
    # Get unique values for filters (с проверкой на наличие колонок)
    nrr_options = ['Все'] 
    dt_options = ['Все']
    flag_options = ['Все']
    delivery_options = ['Все']
    retailer_options = ['Все']
    city_options = ['Все']
    
    if 'NRR' in df.columns:
        nrr_options += sorted(df['NRR'].unique().tolist())
    if 'dt' in df.columns:
        dt_options += sorted(df['dt'].unique().tolist())
    if 'flag' in df.columns:
        flag_options += sorted(df['flag'].unique().tolist())
    if 'type_store_delivery' in df.columns:
        delivery_options += sorted(df['type_store_delivery'].unique().tolist())
    if 'retailer_name' in df.columns:
        retailer_options += sorted(df['retailer_name'].unique().tolist())
    if 'city_category' in df.columns:
        city_options += sorted(df['city_category'].unique().tolist())
    
    # Granulation options
    granulation_options = [
        'Overall Level (общий)',
        'Date Level (по датам)',
        'Retailer Level (по ритейлерам)',
        'City Level (по городам)'
    ]
    
    # Добавляем опции в зависимости от доступных колонок
    if all(col in df.columns for col in ['user_id', 'shipment_id']):
        granulation_options.insert(0, 'Shipment Level (самый детальный)')
        granulation_options.insert(1, 'User Level (по пользователям)')
    
    # Create filters in sidebar
    target_nrr = st.sidebar.selectbox(
        'Целевая группа NRR:',
        options=nrr_options,
        index=0
    )
    
    selected_dates = st.sidebar.multiselect(
        'Дата:',
        options=dt_options,
        default=['Все']
    )
    
    selected_flags = st.sidebar.multiselect(
        'Флаг:',
        options=flag_options,
        default=['Все']
    )
    
    selected_delivery = st.sidebar.multiselect(
        'Тип доставки:',
        options=delivery_options,
        default=['Все']
    )
    
    # Retailer selection (только если есть колонка)
    if 'retailer_name' in df.columns:
        retailer_search = st.sidebar.text_input(
            'Поиск ритейлера:',
            placeholder='Введите часть названия ритейлера...'
        )
        
        # Filter retailers based on search
        if retailer_search:
            filtered_retailers = ['Все'] + sorted([
                retailer for retailer in df['retailer_name'].unique()
                if retailer_search.lower() in str(retailer).lower()
            ])
        else:
            filtered_retailers = retailer_options
        
        selected_retailers = st.sidebar.multiselect(
            'Выбор ритейлера:',
            options=filtered_retailers,
            default=['Все']
        )
    else:
        retailer_search = ""
        selected_retailers = ['Все']
    
    # City selection (только если есть колонка)
    if 'city_category' in df.columns:
        # Filter cities based on selected retailers
        if 'Все' in selected_retailers or not selected_retailers or 'retailer_name' not in df.columns:
            available_cities = city_options
        else:
            filtered_df_cities = df[df['retailer_name'].isin(selected_retailers)]
            available_cities = ['Все'] + sorted(filtered_df_cities['city_category'].unique().tolist())
        
        selected_cities = st.sidebar.multiselect(
            'Город:',
            options=available_cities,
            default=['Все']
        )
    else:
        selected_cities = ['Все']
    
    min_orders = st.sidebar.number_input(
        'Мин. заказов:',
        min_value=1,
        max_value=1000,
        value=10
    )
    
    granulation_level = st.sidebar.selectbox(
        'Уровень детализации:',
        options=granulation_options,
        index=0
    )
    
    # Store filters in session state
    st.session_state.filters = {
        'target_nrr': target_nrr,
        'dates': selected_dates,
        'flags': selected_flags,
        'delivery': selected_delivery,
        'retailers': selected_retailers,
        'cities': selected_cities,
        'retailer_search': retailer_search,
        'min_orders': min_orders,
        'granulation': granulation_level,
        'df': df  # Сохраняем df в session_state
    }
    
    # Buttons in main area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button('🔍 Применить Фильтры и Проверить Данные', use_container_width=True):
            check_data_size()
    
    with col2:
        plot_disabled = st.session_state.get('current_filtered_data') is None
        if st.button('📊 Построить График', use_container_width=True, disabled=plot_disabled):
            create_plot()

def apply_filters():
    """Применение выбранных фильтров к данным"""
    if 'filters' not in st.session_state:
        return None
    
    filters = st.session_state.filters
    df = filters['df']  # Берем df из session_state
    
    filtered_df = df.copy()
    
    # Apply NRR filter (если есть колонка)
    if 'NRR' in df.columns and filters['target_nrr'] != 'Все':
        filtered_df = filtered_df[filtered_df['NRR'] == filters['target_nrr']]
    
    # Apply date filter (если есть колонка)
    if 'dt' in df.columns and 'Все' not in filters['dates']:
        filtered_df = filtered_df[filtered_df['dt'].isin(filters['dates'])]
    
    # Apply flag filter (если есть колонка)
    if 'flag' in df.columns and 'Все' not in filters['flags']:
        filtered_df = filtered_df[filtered_df['flag'].isin(filters['flags'])]
    
    # Apply delivery type filter (если есть колонка)
    if 'type_store_delivery' in df.columns and 'Все' not in filters['delivery']:
        filtered_df = filtered_df[filtered_df['type_store_delivery'].isin(filters['delivery'])]
    
    # Apply retailer filter (если есть колонка)
    if 'retailer_name' in df.columns and 'Все' not in filters['retailers']:
        filtered_df = filtered_df[filtered_df['retailer_name'].isin(filters['retailers'])]
    
    # Apply city filter (если есть колонка)
    if 'city_category' in df.columns and 'Все' not in filters['cities']:
        filtered_df = filtered_df[filtered_df['city_category'].isin(filters['cities'])]
    
    # Apply retailer search filter (если есть колонка)
    if 'retailer_name' in df.columns and filters['retailer_search']:
        filtered_df = filtered_df[filtered_df['retailer_name'].str.contains(filters['retailer_search'], case=False, na=False)]
    
    # Apply minimum orders filter
    filtered_df = filtered_df[filtered_df['Orders delivered'] >= filters['min_orders']]
    
    return filtered_df

def analyze_data_by_granulation():
    """Анализ данных с выбранным уровнем детализации"""
    filtered_df = apply_filters()
    
    if filtered_df is None or len(filtered_df) == 0:
        return None, "Нет данных для выбранных фильтров"
    
    granulation_level = st.session_state.filters['granulation']
    df = st.session_state.filters['df']
    
    # Define grouping columns based on granulation level and available columns
    if granulation_level == 'Shipment Level (самый детальный)' and all(col in df.columns for col in ['user_id', 'shipment_id']):
        group_columns = ['user_id', 'shipment_id']
        entity_name = 'shipments'
    elif granulation_level == 'User Level (по пользователям)' and 'user_id' in df.columns:
        group_columns = ['user_id']
        entity_name = 'users'
    elif granulation_level == 'Retailer Level (по ритейлерам)' and 'retailer_name' in df.columns:
        group_columns = ['retailer_name']
        entity_name = 'retailers'
    elif granulation_level == 'City Level (по городам)' and 'city_category' in df.columns:
        group_columns = ['city_category']
        entity_name = 'cities'
    elif granulation_level == 'Date Level (по датам)' and 'dt' in df.columns:
        group_columns = ['dt']
        entity_name = 'dates'
    else:
        # Overall level - no grouping
        group_columns = []
        entity_name = 'overall'
    
    # Add optional grouping columns if available
    optional_columns = ['dt', 'flag', 'type_store_delivery', 'retailer_name', 'city_category']
    for col in optional_columns:
        if col in df.columns and col not in group_columns:
            group_columns.append(col)
    
    # Group data if we have grouping columns
    if group_columns:
        grouped_metrics = filtered_df.groupby(group_columns).agg({
            'CP1 - ads': 'sum',
            'Orders delivered': 'sum',
            'Promo': 'sum',
            'GMV NoP - ads': 'sum',
            'Direct fullfillment': 'sum'
        }).reset_index()
    else:
        # Overall aggregation
        grouped_metrics = pd.DataFrame({
            'CP1 - ads': [filtered_df['CP1 - ads'].sum()],
            'Orders delivered': [filtered_df['Orders delivered'].sum()],
            'Promo': [filtered_df['Promo'].sum()],
            'GMV NoP - ads': [filtered_df['GMV NoP - ads'].sum()],
            'Direct fullfillment': [filtered_df['Direct fullfillment'].sum()]
        })
    
    # Calculate per-order metrics
    grouped_metrics['CP1_ads_per_order'] = grouped_metrics['CP1 - ads'] / grouped_metrics['Orders delivered']
    grouped_metrics['promo_per_order'] = grouped_metrics['Promo'] / grouped_metrics['Orders delivered']
    grouped_metrics['fulfillment_per_order'] = grouped_metrics['Direct fullfillment'] / grouped_metrics['Orders delivered']
    grouped_metrics['gmv_per_order'] = grouped_metrics['GMV NoP - ads'] / grouped_metrics['Orders delivered']
    
    return grouped_metrics, entity_name

def check_data_size():
    """Проверка размера данных"""
    st.info("🔄 Проверка данных с текущими фильтрами...")
    
    # Get filtered data with selected granulation
    filtered_data, entity_name = analyze_data_by_granulation()
    
    if filtered_data is None:
        st.error("❌ Нет данных для выбранных фильтров")
        st.session_state.current_filtered_data = None
        return
    
    if isinstance(filtered_data, str):  # Error case
        st.error(f"❌ {filtered_data}")
        st.session_state.current_filtered_data = None
        return
    
    num_points = len(filtered_data)
    st.success(f"✅ Найдено {num_points} {entity_name}")
    
    # Show summary statistics
    st.subheader("📊 Статистика CP1-ads для выбранных данных:")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Среднее", f"{filtered_data['CP1_ads_per_order'].mean():.0f}")
    with col2:
        st.metric("Медиана", f"{filtered_data['CP1_ads_per_order'].median():.0f}")
    with col3:
        st.metric("Минимум", f"{filtered_data['CP1_ads_per_order'].min():.0f}")
    with col4:
        st.metric("Максимум", f"{filtered_data['CP1_ads_per_order'].max():.0f}")
    
    # Store filtered data for plotting
    st.session_state.current_filtered_data = filtered_data
    st.session_state.current_entity_name = entity_name
    
    st.success("🎨 Данные готовы для построения графика!")

def create_plot():
    """Создание графика после подтверждения"""
    if 'current_filtered_data' not in st.session_state or st.session_state.current_filtered_data is None:
        st.error("❌ Нет данных для построения графика. Сначала примените фильтры.")
        return
    
    filtered_data = st.session_state.current_filtered_data
    entity_name = st.session_state.current_entity_name
    
    st.info(f"📊 Построение графика для {len(filtered_data)} {entity_name}...")
    
    # Create simple plot (упрощенная версия)
    fig = go.Figure()
    
    fig.add_trace(go.Scatter3d(
        x=filtered_data['promo_per_order'],
        y=filtered_data['fulfillment_per_order'],
        z=filtered_data['gmv_per_order'],
        mode='markers',
        marker=dict(
            size=8,
            color=filtered_data['CP1_ads_per_order'],
            colorscale='RdYlGn',
            colorbar=dict(title="CP1-ads per Order"),
            showscale=True,
            opacity=0.7
        ),
        text=[f"CP1/заказ: {cp1:.0f}" for cp1 in filtered_data['CP1_ads_per_order']],
        hovertemplate='%{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title='3D Анализ: Промо vs Фулфилмент vs GMV',
        scene=dict(
            xaxis_title='Промо на заказ',
            yaxis_title='Фулфилмент на заказ',
            zaxis_title='GMV на заказ'
        ),
        width=800,
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.success("✅ График создан успешно!")

if __name__ == "__main__":
    main()