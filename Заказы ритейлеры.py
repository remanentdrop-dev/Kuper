import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from io import StringIO

# Initialize session state for storing data
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_filtered_data' not in st.session_state:
    st.session_state.current_filtered_data = None
if 'current_entity_name' not in st.session_state:
    st.session_state.current_entity_name = None

def setup_streamlit_filters(df):
    """Настройка фильтров в Streamlit"""
    
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
    
    # Create filters in columns
    col1, col2 = st.columns(2)
    
    with col1:
        target_nrr = st.selectbox(
            'Целевая группа NRR:',
            options=nrr_options,
            index=nrr_options.index('Старичок') if 'Старичок' in nrr_options else 0
        )
        
        min_orders = st.number_input(
            'Мин. заказов:',
            min_value=1,
            max_value=1000,
            value=10
        )
        
        selected_dates = st.multiselect(
            'Дата:',
            options=dt_options,
            default=['Все']
        )
        
        selected_flags = st.multiselect(
            'Флаг:',
            options=flag_options,
            default=['Все']
        )
        
    with col2:
        selected_delivery = st.multiselect(
            'Тип доставки:',
            options=delivery_options,
            default=['Все']
        )
        
        granulation_level = st.selectbox(
            'Уровень детализации:',
            options=granulation_options,
            index=0
        )
        
        selected_cities = st.multiselect(
            'Город:',
            options=city_options,
            default=['Все']
        )
    
    # Retailer search and selection
    retailer_search = st.text_input(
        'Поиск ритейлера:',
        placeholder='Введите часть названия ритейлера...',
        value=''
    )
    
    # Filter retailers based on search
    if retailer_search:
        filtered_retailers = ['Все'] + sorted([
            retailer for retailer in df['retailer_name'].unique()
            if retailer_search.lower() in retailer.lower()
        ])
    else:
        filtered_retailers = retailer_options
    
    selected_retailers = st.multiselect(
        'Выбор ритейлера:',
        options=filtered_retailers,
        default=['Все']
    )
    
    return {
        'target_nrr': target_nrr,
        'min_orders': min_orders,
        'selected_dates': selected_dates,
        'selected_flags': selected_flags,
        'selected_delivery': selected_delivery,
        'selected_retailers': selected_retailers,
        'selected_cities': selected_cities,
        'granulation_level': granulation_level,
        'retailer_search': retailer_search
    }

def apply_filters(df, filters):
    """Применение выбранных фильтров к данным"""
    filtered_df = df.copy()
    
    # Apply NRR filter
    if filters['target_nrr'] != 'Все':
        filtered_df = filtered_df[filtered_df['NRR'] == filters['target_nrr']]
    
    # Apply date filter
    if 'Все' not in filters['selected_dates']:
        filtered_df = filtered_df[filtered_df['dt'].isin(filters['selected_dates'])]
    
    # Apply flag filter
    if 'Все' not in filters['selected_flags']:
        filtered_df = filtered_df[filtered_df['flag'].isin(filters['selected_flags'])]
    
    # Apply delivery type filter
    if 'Все' not in filters['selected_delivery']:
        filtered_df = filtered_df[filtered_df['type_store_delivery'].isin(filters['selected_delivery'])]
    
    # Apply retailer filter
    if 'Все' not in filters['selected_retailers']:
        filtered_df = filtered_df[filtered_df['retailer_name'].isin(filters['selected_retailers'])]
    
    # Apply city filter
    if 'Все' not in filters['selected_cities']:
        filtered_df = filtered_df[filtered_df['city_category'].isin(filters['selected_cities'])]
    
    # Apply retailer search filter
    if filters['retailer_search']:
        filtered_df = filtered_df[filtered_df['retailer_name'].str.contains(filters['retailer_search'], case=False, na=False)]
    
    # Apply minimum orders filter
    filtered_df = filtered_df[filtered_df['Orders delivered'] >= filters['min_orders']]
    
    return filtered_df

def analyze_data_by_granulation(df, filters):
    """Анализ данных с выбранным уровнем детализации"""
    filtered_df = apply_filters(df, filters)
    
    if len(filtered_df) == 0:
        return None, "Нет данных для выбранных фильтров"
    
    granulation_level = filters['granulation_level']
    
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

def create_3d_scatter_plot(filtered_data, entity_name, filters):
    """Создание 3D scatter plot с цветами по CP1-ads"""
    
    # Calculate color scale range based on data
    cp1_min = filtered_data['CP1_ads_per_order'].quantile(0.05)  # 5th percentile to avoid outliers
    cp1_max = filtered_data['CP1_ads_per_order'].quantile(0.95)  # 95th percentile to avoid outliers
    
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
            colorscale='RdYlGn',  # Red to Yellow to Green
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
    filter_info = f"NRR: {filters['target_nrr']} | Детализация: {filters['granulation_level']}"
    if 'Все' not in filters['selected_dates']:
        filter_info += f" | Даты: {', '.join(filters['selected_dates'])}"
    if 'Все' not in filters['selected_flags']:
        filter_info += f" | Флаги: {', '.join(filters['selected_flags'])}"
    if 'Все' not in filters['selected_delivery']:
        filter_info += f" | Доставка: {', '.join(filters['selected_delivery'])}"
    if 'Все' not in filters['selected_retailers']:
        filter_info += f" | Ритейлеры: {len(filters['selected_retailers'])} выбранных"
    if 'Все' not in filters['selected_cities']:
        filter_info += f" | Города: {', '.join(filters['selected_cities'])}"
    
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

def check_data_size(df, filters):
    """Проверка размера данных и предупреждение если слишком много точек"""
    
    st.info("🔄 Проверка данных с текущими фильтрами...")
    
    # Get filtered data with selected granulation
    filtered_data, entity_name = analyze_data_by_granulation(df, filters)
    
    if isinstance(filtered_data, str):  # Error case
        st.error(f"❌ {filtered_data}")
        return False, None, None
    
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
            st.metric("Пользователей", filtered_data['user_id'].nunique())
        with col2:
            st.metric("Ритейлеров", filtered_data['retailer_name'].nunique())
    
    # Warning for large datasets
    if num_points > 10000:
        st.warning(f"⚠️ ВНИМАНИЕ: Выбрано {num_points} {entity_name}!")
        st.info("График может работать медленно или быть перегруженным. Рекомендуется:")
        st.info("- Выбрать более высокий уровень детализации")
        st.info("- Сузить фильтры по датам/ритейлерам/городам")
    elif num_points > 5000:
        st.info(f"💡 Подсказка: {num_points} {entity_name} - график будет отзывчивым")
    else:
        st.success(f"✅ Отлично! {num_points} {entity_name} - идеальный размер для анализа")
    
    return True, filtered_data, entity_name

def main():
    st.set_page_config(page_title="3D Анализ данных", layout="wide")
    st.title("🎯 3D Анализ данных с выбором детализации")
    
    # File upload
    st.sidebar.header("📁 Загрузка данных")
    uploaded_file = st.sidebar.file_uploader("Загрузите CSV файл", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Read the CSV file
            df = pd.read_csv(uploaded_file)
            st.session_state.df = df
            
            st.sidebar.success(f"✅ Файл загружен успешно! Строк: {len(df)}")
            
            # Data structure check
            st.sidebar.subheader("🔍 Проверка структуры данных:")
            st.sidebar.write(f"Колонки: {df.columns.tolist()}")
            
            # Check required columns
            required_columns = ['user_id', 'shipment_id', 'retailer_name', 'city_category']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.sidebar.error(f"❌ Отсутствуют колонки: {missing_columns}")
                st.sidebar.info("Убедитесь, что данные содержат user_id и shipment_id для детального анализа")
            else:
                st.sidebar.success("✅ Все необходимые колонки присутствуют")
            
            # Setup filters
            st.header("🎛️ Настройка фильтров")
            filters = setup_streamlit_filters(df)
            
            # Buttons
            col1, col2 = st.columns(2)
            with col1:
                apply_filters_btn = st.button(
                    'Применить Фильтры и Проверить Данные',
                    type='primary',
                    use_container_width=True
                )
            with col2:
                create_plot_btn = st.button(
                    'Построить График',
                    type='secondary',
                    use_container_width=True
                )
            
            # Instructions
            with st.expander("📝 Инструкции по использованию"):
                st.markdown("""
                1. **Выберите уровень детализации данных:**
                   - **Shipment Level** - отдельные отгрузки (самый детальный)
                   - **User Level** - агрегация по пользователям
                   - **Retailer Level** - агрегация по ритейлерам
                   - **City Level** - агрегация по городам (самый общий)
                
                2. **Выберите другие фильтры** (NRR, даты, флаги и т.д.)
                3. **Используйте поиск ритейлера** для фильтрации списка
                4. **Выберите ритейлеров** из списка
                5. **Выберите города** (список обновится после выбора ритейлеров)
                6. **Нажмите 'Применить Фильтры и Проверить Данные'**
                7. **Если количество точек приемлемо, нажмите 'Построить График'**
                """)
            
            # Apply filters and check data
            if apply_filters_btn:
                success, filtered_data, entity_name = check_data_size(df, filters)
                if success:
                    st.session_state.current_filtered_data = filtered_data
                    st.session_state.current_entity_name = entity_name
                    st.success("✅ Данные готовы для построения графика!")
            
            # Create plot
            if create_plot_btn:
                if st.session_state.current_filtered_data is not None:
                    st.header("🎨 3D Визуализация")
                    
                    filtered_data = st.session_state.current_filtered_data
                    entity_name = st.session_state.current_entity_name
                    num_points = len(filtered_data)
                    
                    st.info(f"📊 Построение графика для {num_points} {entity_name}...")
                    
                    # Create the plot
                    fig = create_3d_scatter_plot(filtered_data, entity_name, filters)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.success("✅ График создан успешно!")
                    
                    # Interpretation guide
                    with st.expander("💡 Интерпретация графика"):
                        st.markdown(f"""
                        **Уровень детализации:** {filters['granulation_level']}
                        
                        **Оси:**
                        - **Ось X**: Промо расходы на заказ
                        - **Ось Y**: Фулфилмент расходы на заказ
                        - **Ось Z**: GMV на заказ
                        
                        **Цвет точек**: CP1-ads на заказ (красный = низкий, зеленый = высокий)
                        - **Каждая точка**: {entity_name}
                        """)
                    
                    # Additional insights
                    st.subheader("📈 Быстрая аналитика")
                    
                    # Top performers by CP1-ads
                    st.write("**Топ-3 по CP1-ads:**")
                    top_entities = filtered_data.nlargest(3, 'CP1_ads_per_order')
                    
                    for i, (_, entity) in enumerate(top_entities.iterrows(), 1):
                        if entity_name == 'shipments':
                            name = f"{entity['retailer_name']} (User: {entity['user_id'][:8]}...)"
                        elif entity_name == 'users':
                            name = f"User: {entity['user_id'][:8]}... ({entity['retailer_name']})"
                        elif entity_name == 'retailers':
                            name = entity['retailer_name']
                        elif entity_name == 'cities':
                            name = entity['city_category']
                        elif entity_name == 'ret+city':
                            name = f"{entity['retailer_name']} - {entity['city_category']}"
                        
                        st.write(f"{i}. **{name}** (CP1: {entity['CP1_ads_per_order']:.0f})")
                
                else:
                    st.error("❌ Нет данных для построения графика. Сначала примените фильтры.")
        
        except Exception as e:
            st.error(f"❌ Ошибка при чтении файла: {str(e)}")
    
    else:
        st.info("👆 Пожалуйста, загрузите CSV файл для начала анализа")
        
        # Show expected data structure
        with st.expander("📋 Ожидаемая структура данных"):
            st.markdown("""
            Файл должен содержать следующие колонки:
            - `user_id`: идентификатор пользователя
            - `shipment_id`: идентификатор отгрузки
            - `retailer_name`: название ритейлера
            - `city_category`: категория города
            - `NRR`: целевая группа
            - `dt`: дата
            - `flag`: флаг
            - `type_store_delivery`: тип доставки
            - `CP1 - ads`: расходы CP1
            - `Orders delivered`: доставленные заказы
            - `Promo`: промо расходы
            - `Promo Новичка`: промо новичка
            - `GMV NoP - ads`: GMV
            - `Direct fullfillment`: прямые расходы на фулфилмент
            """)

if __name__ == "__main__":
    main()