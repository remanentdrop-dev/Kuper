import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import io

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
        help="Файл должен содержать колонки: user_id, shipment_id, retailer_name, city_category, NRR, dt, flag, type_store_delivery, и метрики"
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
            
            # Check required columns
            required_columns = ['user_id', 'shipment_id', 'retailer_name', 'city_category', 'NRR', 'dt', 'flag', 
                              'type_store_delivery', 'CP1 - ads', 'Orders delivered', 'Promo', 'GMV NoP - ads', 'Direct fullfillment']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"❌ Отсутствуют необходимые колонки: {missing_columns}")
                return
            
            # Initialize session state for filtered data
            if 'current_filtered_data' not in st.session_state:
                st.session_state.current_filtered_data = None
            if 'current_entity_name' not in st.session_state:
                st.session_state.current_entity_name = None
            
            # Setup filters
            setup_interactive_filters(df)
            
        except Exception as e:
            st.error(f"❌ Ошибка при чтении файла: {str(e)}")
    else:
        st.info("👆 Пожалуйста, загрузите CSV файл в боковой панели чтобы начать анализ")
        
        # Show expected data structure
        with st.expander("📋 Ожидаемая структура данных"):
            st.markdown("""
            **Обязательные колонки:**
            - `user_id`: ID пользователя
            - `shipment_id`: ID отгрузки  
            - `retailer_name`: Название ритейлера
            - `city_category`: Категория города
            - `NRR`: Целевая группа NRR
            - `dt`: Дата
            - `flag`: Флаг/сегмент
            - `type_store_delivery`: Тип доставки
            
            **Метрики:**
            - `CP1 - ads`: Расходы на рекламу
            - `Orders delivered`: Доставленные заказы
            - `Promo`: Промо расходы
            - `GMV NoP - ads`: GMV без рекламы
            - `Direct fullfillment`: Фулфилмент расходы
            """)

def setup_interactive_filters(df):
    """Настройка интерактивных фильтров в Streamlit"""
    
    st.sidebar.header("🎛️ Фильтры")
    
    # Get unique values for filters
    nrr_options = sorted(df['NRR'].unique())
    dt_options = ['Все'] + sorted(df['dt'].unique().tolist())
    flag_options = ['Все'] + sorted(df['flag'].unique().tolist())
    delivery_options = ['Все'] + sorted(df['type_store_delivery'].unique().tolist())
    retailer_options = ['Все'] + sorted(df['retailer_name'].unique().tolist())
    city_options = ['Все'] + sorted(df['city_category'].unique().tolist())
    
    # Granulation options
    granulation_options = [
        'Shipment Level (самый детальный)',
        'User Level (по пользователям)', 
        'Retailer Level (по ритейлерам)',
        'City Level (по городам)',
        'Retailer + City Level'
    ]
    
    # Create filters in sidebar
    target_nrr = st.sidebar.selectbox(
        'Целевая группа NRR:',
        options=nrr_options,
        index=0 if len(nrr_options) > 0 else 0
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
    
    # Retailer search and selection
    retailer_search = st.sidebar.text_input(
        'Поиск ритейлера:',
        placeholder='Введите часть названия ритейлера...'
    )
    
    # Filter retailers based on search
    if retailer_search:
        filtered_retailers = ['Все'] + sorted([
            retailer for retailer in df['retailer_name'].unique()
            if retailer_search.lower() in retailer.lower()
        ])
    else:
        filtered_retailers = retailer_options
    
    selected_retailers = st.sidebar.multiselect(
        'Выбор ритейлера:',
        options=filtered_retailers,
        default=['Все']
    )
    
    # Filter cities based on selected retailers
    if 'Все' in selected_retailers or not selected_retailers:
        available_cities = city_options
    else:
        filtered_df_cities = df[df['retailer_name'].isin(selected_retailers)]
        available_cities = ['Все'] + sorted(filtered_df_cities['city_category'].unique().tolist())
    
    selected_cities = st.sidebar.multiselect(
        'Город:',
        options=available_cities,
        default=['Все']
    )
    
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
        'granulation': granulation_level
    }
    
    # Buttons in main area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button('🔍 Применить Фильтры и Проверить Данные', use_container_width=True):
            check_data_size(df)
    
    with col2:
        if st.button('📊 Построить График', use_container_width=True, 
                    disabled=st.session_state.current_filtered_data is None):
            create_plot()

def apply_filters(df):
    """Применение выбранных фильтров к данным"""
    filters = st.session_state.filters
    filtered_df = df.copy()
    
    # Apply NRR filter
    if filters['target_nrr'] != 'Все':
        filtered_df = filtered_df[filtered_df['NRR'] == filters['target_nrr']]
    
    # Apply date filter
    if 'Все' not in filters['dates']:
        filtered_df = filtered_df[filtered_df['dt'].isin(filters['dates'])]
    
    # Apply flag filter
    if 'Все' not in filters['flags']:
        filtered_df = filtered_df[filtered_df['flag'].isin(filters['flags'])]
    
    # Apply delivery type filter
    if 'Все' not in filters['delivery']:
        filtered_df = filtered_df[filtered_df['type_store_delivery'].isin(filters['delivery'])]
    
    # Apply retailer filter
    if 'Все' not in filters['retailers']:
        filtered_df = filtered_df[filtered_df['retailer_name'].isin(filters['retailers'])]
    
    # Apply city filter
    if 'Все' not in filters['cities']:
        filtered_df = filtered_df[filtered_df['city_category'].isin(filters['cities'])]
    
    # Apply retailer search filter
    if filters['retailer_search']:
        filtered_df = filtered_df[filtered_df['retailer_name'].str.contains(filters['retailer_search'], case=False, na=False)]
    
    # Apply minimum orders filter
    filtered_df = filtered_df[filtered_df['Orders delivered'] >= filters['min_orders']]
    
    return filtered_df

def analyze_data_by_granulation(df):
    """Анализ данных с выбранным уровнем детализации"""
    filtered_df = apply_filters(df)
    
    if len(filtered_df) == 0:
        return None, "Нет данных для выбранных фильтров"
    
    granulation_level = st.session_state.filters['granulation']
    
    # Define grouping columns based on granulation level
    if granulation_level == 'Shipment Level (самый детальный)':
        group_columns = ['user_id', 'shipment_id', 'dt', 'flag', 'type_store_delivery', 'retailer_name', 'city_category']
        entity_name = 'shipments'
        
    elif granulation_level == 'User Level (по пользователям)':
        group_columns = ['user_id', 'dt', 'flag', 'type_store_delivery', 'retailer_name', 'city_category']
        entity_name = 'users'
        
    elif granulation_level == 'Retailer Level (по ритейлерам)':
        group_columns = ['retailer_name', 'dt', 'flag', 'type_store_delivery']
        entity_name = 'retailers'
        
    elif granulation_level == 'City Level (по городам)':
        group_columns = ['city_category', 'dt', 'flag', 'type_store_delivery']
        entity_name = 'cities'

    elif granulation_level == 'Retailer + City Level':
        group_columns = ['retailer_name', 'dt', 'flag', 'type_store_delivery', 'city_category']
        entity_name = 'ret+city'
    
    # Group data by selected granulation level
    grouped_metrics = filtered_df.groupby(group_columns).agg({
        'CP1 - ads': 'sum',
        'Orders delivered': 'sum',
        'Promo': 'sum',
        'Promo Новичка': 'sum',
        'GMV NoP - ads': 'sum',
        'Direct fullfillment': 'sum'
    }).reset_index()
    
    # Calculate per-order metrics
    grouped_metrics['CP1_ads_per_order'] = grouped_metrics['CP1 - ads'] / grouped_metrics['Orders delivered']
    grouped_metrics['promo_per_order'] = grouped_metrics['Promo'] / grouped_metrics['Orders delivered']
    grouped_metrics['fulfillment_per_order'] = grouped_metrics['Direct fullfillment'] / grouped_metrics['Orders delivered']
    grouped_metrics['gmv_per_order'] = grouped_metrics['GMV NoP - ads'] / grouped_metrics['Orders delivered']
    
    return grouped_metrics, entity_name

def create_3d_scatter_plot(filtered_data, entity_name):
    """Создание 3D scatter plot с цветами по CP1-ads"""
    
    # Calculate color scale range based on data
    cp1_min = filtered_data['CP1_ads_per_order'].quantile(0.05)
    cp1_max = filtered_data['CP1_ads_per_order'].quantile(0.95)
    
    fig = go.Figure()
    
    # Create hover text based on granulation level
    if entity_name == 'shipments':
        hover_text = filtered_data.apply(
            lambda x: f"Ритейлер: {x['retailer_name']}<br>"
                     f"Город: {x['city_category']}<br>"
                     f"Сегмент: {x['flag']}<br>"
                     f"Доставка: {x['type_store_delivery']}<br>"
                     f"Дата: {x['dt']}<br>"
                     f"User ID: {x['user_id']}<br>"
                     f"Shipment ID: {x['shipment_id']}<br>"
                     f"Заказы: {x['Orders delivered']}<br>"
                     f"CP1/заказ: {x['CP1_ads_per_order']:.0f}<br>"
                     f"Промо/заказ: {x['promo_per_order']:.0f}<br>"
                     f"Фулфилмент/заказ: {x['fulfillment_per_order']:.0f}<br>"
                     f"GMV/заказ: {x['gmv_per_order']:.0f}", axis=1)
        
    elif entity_name == 'users':
        hover_text = filtered_data.apply(
            lambda x: f"Ритейлер: {x['retailer_name']}<br>"
                     f"Город: {x['city_category']}<br>"
                     f"Сегмент: {x['flag']}<br>"
                     f"Доставка: {x['type_store_delivery']}<br>"
                     f"Дата: {x['dt']}<br>"
                     f"User ID: {x['user_id']}<br>"
                     f"Всего заказов: {x['Orders delivered']}<br>"
                     f"CP1/заказ: {x['CP1_ads_per_order']:.0f}<br>"
                     f"Промо/заказ: {x['promo_per_order']:.0f}<br>"
                     f"Фулфилмент/заказ: {x['fulfillment_per_order']:.0f}<br>"
                     f"GMV/заказ: {x['gmv_per_order']:.0f}", axis=1)
        
    elif entity_name == 'retailers':
        hover_text = filtered_data.apply(
            lambda x: f"Ритейлер: {x['retailer_name']}<br>"
                     f"Сегмент: {x['flag']}<br>"
                     f"Доставка: {x['type_store_delivery']}<br>"
                     f"Дата: {x['dt']}<br>"
                     f"Всего заказов: {x['Orders delivered']}<br>"
                     f"CP1/заказ: {x['CP1_ads_per_order']:.0f}<br>"
                     f"Промо/заказ: {x['promo_per_order']:.0f}<br>"
                     f"Фулфилмент/заказ: {x['fulfillment_per_order']:.0f}<br>"
                     f"GMV/заказ: {x['gmv_per_order']:.0f}", axis=1)
        
    elif entity_name == 'cities':
        hover_text = filtered_data.apply(
            lambda x: f"Город: {x['city_category']}<br>"
                     f"Сегмент: {x['flag']}<br>"
                     f"Доставка: {x['type_store_delivery']}<br>"
                     f"Дата: {x['dt']}<br>"
                     f"Всего заказов: {x['Orders delivered']}<br>"
                     f"CP1/заказ: {x['CP1_ads_per_order']:.0f}<br>"
                     f"Промо/заказ: {x['promo_per_order']:.0f}<br>"
                     f"Фулфилмент/заказ: {x['fulfillment_per_order']:.0f}<br>"
                     f"GMV/заказ: {x['gmv_per_order']:.0f}", axis=1)
        
    elif entity_name == 'ret+city':
        hover_text = filtered_data.apply(
            lambda x: f"Ритейлер: {x['retailer_name']}<br>"
                     f"Город: {x['city_category']}<br>"
                     f"Сегмент: {x['flag']}<br>"
                     f"Доставка: {x['type_store_delivery']}<br>"
                     f"Дата: {x['dt']}<br>"
                     f"Всего заказов: {x['Orders delivered']}<br>"
                     f"CP1/заказ: {x['CP1_ads_per_order']:.0f}<br>"
                     f"Промо/заказ: {x['promo_per_order']:.0f}<br>"
                     f"Фулфилмент/заказ: {x['fulfillment_per_order']:.0f}<br>"
                     f"GMV/заказ: {x['gmv_per_order']:.0f}", axis=1)
    
    # Add scatter plot
    fig.add_trace(go.Scatter3d(
        x=filtered_data['promo_per_order'],
        y=filtered_data['fulfillment_per_order'],
        z=filtered_data['gmv_per_order'],
        mode='markers',
        marker=dict(
            size=8 if entity_name in ['cities', 'retailers'] else 6,
            color=filtered_data['CP1_ads_per_order'],
            colorscale='RdYlGn',
            colorbar=dict(title="CP1-ads per Order"),
            showscale=True,
            cmin=cp1_min,
            cmax=cp1_max,
            opacity=0.7
        ),
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        name=entity_name.capitalize()
    ))
    
    # Build filter info for title
    filters = st.session_state.filters
    filter_info = f"NRR: {filters['target_nrr']} | Детализация: {filters['granulation']}"
    if 'Все' not in filters['dates']:
        filter_info += f" | Даты: {', '.join(filters['dates'])}"
    if 'Все' not in filters['flags']:
        filter_info += f" | Флаги: {', '.join(filters['flags'])}"
    if 'Все' not in filters['delivery']:
        filter_info += f" | Доставка: {', '.join(filters['delivery'])}"
    if 'Все' not in filters['retailers']:
        filter_info += f" | Ритейлеры: {len(filters['retailers'])} выбранных"
    if 'Все' not in filters['cities']:
        filter_info += f" | Города: {', '.join(filters['cities'])}"
    
    if filters['retailer_search']:
        filter_info += f" | Поиск: '{filters['retailer_search']}'"
    
    fig.update_layout(
        title=f'3D Анализ: Промо vs Фулфилмент vs GMV<br><sub>{filter_info}</sub>',
        scene=dict(
            xaxis_title='Промо на заказ',
            yaxis_title='Фулфилмент на заказ',
            zaxis_title='GMV на заказ',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        ),
        width=1000,
        height=800
    )
    
    return fig

def check_data_size(df):
    """Проверка размера данных и предупреждение если слишком много точек"""
    st.info("🔄 Проверка данных с текущими фильтрами...")
    
    # Get filtered data with selected granulation
    filtered_data, entity_name = analyze_data_by_granulation(df)
    
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
    
    # Show unique counts based on granulation level
    st.subheader("👥 Уникальные значения:")
    if entity_name == 'shipments':
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Пользователей", filtered_data['user_id'].nunique())
        with col2:
            st.metric("Ритейлеров", filtered_data['retailer_name'].nunique())
        with col3:
            st.metric("Городов", filtered_data['city_category'].nunique())
    elif entity_name == 'users':
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Пользователей", filtered_data['user_id'].nunique())
        with col2:
            st.metric("Ритейлеров", filtered_data['retailer_name'].nunique())
    elif entity_name == 'retailers':
        st.metric("Ритейлеров", filtered_data['retailer_name'].nunique())
    elif entity_name == 'cities':
        st.metric("Городов", filtered_data['city_category'].nunique())
    elif entity_name == 'ret+city':
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Ритейлеров", filtered_data['retailer_name'].nunique())
        with col2:
            st.metric("Городов", filtered_data['city_category'].nunique())
    
    # Warning for large datasets
    if num_points > 10000:
        st.warning(f"⚠️ ВНИМАНИЕ: Выбрано {num_points} {entity_name}!")
        st.info("""
        **Рекомендации:**
        - Выберите более высокий уровень детализации
        - Сузьте фильтры по датам/ритейлерам/городам
        """)
    elif num_points > 5000:
        st.info(f"💡 Подсказка: {num_points} {entity_name} - график будет отзывчивым")
    else:
        st.success(f"✅ Отлично! {num_points} {entity_name} - идеальный размер для анализа")
    
    # Store filtered data for plotting
    st.session_state.current_filtered_data = filtered_data
    st.session_state.current_entity_name = entity_name
    
    st.success("🎨 Данные готовы для построения графика!")

def create_plot():
    """Создание графика после подтверждения"""
    if st.session_state.current_filtered_data is None:
        st.error("❌ Нет данных для построения графика. Сначала примените фильтры.")
        return
    
    filtered_data = st.session_state.current_filtered_data
    entity_name = st.session_state.current_entity_name
    num_points = len(filtered_data)
    
    st.info(f"📊 Построение графика для {num_points} {entity_name}...")
    
    # Create the plot
    fig = create_3d_scatter_plot(filtered_data, entity_name)
    st.plotly_chart(fig, use_container_width=True)
    
    st.success("✅ График создан успешно!")
    
    # Additional insights
    st.subheader("💡 Интерпретация:")
    st.markdown(f"""
    **Уровень детализации:** {st.session_state.filters['granulation']}
    - **Ось X**: Промо расходы на заказ
    - **Ось Y**: Фулфилмент расходы на заказ  
    - **Ось Z**: GMV на заказ
    - **Цвет**: CP1-ads на заказ (красный = низкий, зеленый = высокий)
    - **Каждая точка**: {entity_name}
    """)
    
    # Top performers by CP1-ads
    st.subheader("📈 Топ-3 по CP1-ads:")
    top_entities = filtered_data.nlargest(3, 'CP1_ads_per_order')
    
    for i, (_, entity) in enumerate(top_entities.iterrows(), 1):
        if entity_name == 'shipments':
            name = f"{entity['retailer_name']} (User: {str(entity['user_id'])[:8]}...)"
        elif entity_name == 'users':
            name = f"User: {str(entity['user_id'])[:8]}... ({entity['retailer_name']})"
        elif entity_name == 'retailers':
            name = entity['retailer_name']
        elif entity_name == 'cities':
            name = entity['city_category']
        elif entity_name == 'ret+city':
            name = f"{entity['retailer_name']} - {entity['city_category']}"
        
        st.write(f"{i}. **{name}** (CP1: {entity['CP1_ads_per_order']:.0f})")

if __name__ == "__main__":
    main()